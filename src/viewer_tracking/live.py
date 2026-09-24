from __future__ import annotations

import csv
import math
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np

from .geometry import CameraModel, DepthCalibration, estimate_viewer_position
from .models import EyePair, ViewerPosition
from .trackers import Tracker, create_tracker

# Typical adult interpupillary distance. Used only when no measured calibration exists.
FALLBACK_EYE_SEPARATION_MM = 63.0
CALIBRATION_SAMPLES = 30
PREVIEW_WIDTH_PX = 640
CAMERA_RETRY_S = 1.0


@dataclass(frozen=True)
class ScreenGeometry:
    """Physical layout of the display the parallax window is drawn on.

    Defaults describe the 13-inch MacBook Pro reference machine: a 286 x 179 mm
    panel with the camera centred about 8 mm above its top edge.
    """

    width_mm: float = 286.0
    height_mm: float = 179.0
    camera_above_top_mm: float = 8.0

    @property
    def camera_above_centre_mm(self) -> float:
        return self.height_mm / 2.0 + self.camera_above_top_mm


@dataclass(frozen=True)
class EyePosition:
    """Eye midpoint relative to the screen centre, as seen from the viewer.

    Positive x points to the viewer's right, positive y points up, and z is the
    distance from the screen plane.
    """

    x_mm: float
    y_mm: float
    z_mm: float


def camera_to_screen(position: ViewerPosition, screen: ScreenGeometry) -> EyePosition:
    # The camera faces the viewer, so its image x axis is mirrored relative to the viewer,
    # and its y axis points down from a lens that sits above the screen centre.
    return EyePosition(
        x_mm=-position.x_mm,
        y_mm=screen.camera_above_centre_mm - position.y_mm,
        z_mm=position.z_mm,
    )


class OneEuroFilter:
    """Speed-adaptive low-pass filter (Casiez et al., 2012).

    Slow movement is smoothed heavily to suppress stationary jitter, while fast
    movement raises the cutoff so the scene does not lag behind the viewer.
    """

    def __init__(
        self,
        min_cutoff_hz: float = 1.0,
        beta: float = 0.02,
        derivative_cutoff_hz: float = 1.0,
    ) -> None:
        self.min_cutoff_hz = min_cutoff_hz
        self.beta = beta
        self.derivative_cutoff_hz = derivative_cutoff_hz
        self._value: float | None = None
        self._derivative = 0.0
        self._time: float | None = None

    def reset(self) -> None:
        self._value = None
        self._derivative = 0.0
        self._time = None

    def __call__(self, value: float, time_s: float) -> float:
        if self._value is None or self._time is None or time_s <= self._time:
            self._value = value
            self._time = time_s
            return value

        elapsed = time_s - self._time
        derivative = (value - self._value) / elapsed
        self._derivative = _blend(
            self._derivative, derivative, _alpha(self.derivative_cutoff_hz, elapsed)
        )
        cutoff = self.min_cutoff_hz + self.beta * abs(self._derivative)
        self._value = _blend(self._value, value, _alpha(cutoff, elapsed))
        self._time = time_s
        return self._value


def _alpha(cutoff_hz: float, elapsed_s: float) -> float:
    time_constant = 1.0 / (2.0 * math.pi * cutoff_hz)
    return 1.0 / (1.0 + time_constant / elapsed_s)


def _blend(previous: float, current: float, alpha: float) -> float:
    return previous + alpha * (current - previous)


def load_calibrations(path: Path) -> dict[str, float]:
    """Read per-method reference eye separations written by the benchmark."""
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        return {
            row["method"]: float(row["reference_eye_separation_px"])
            for row in csv.DictReader(handle)
            if row.get("reference_eye_separation_px")
        }


def fallback_eye_separation_px(camera: CameraModel, reference_distance_mm: float) -> float:
    return camera.focal_length_px * FALLBACK_EYE_SEPARATION_MM / reference_distance_mm


@dataclass(frozen=True)
class LiveSnapshot:
    method: str
    calibration_source: str
    reference_eye_separation_px: float
    detected: bool = False
    eyes: EyePair | None = None
    eye_position: EyePosition | None = None
    smoothed_position: EyePosition | None = None
    latency_ms: float | None = None
    camera_fps: float = 0.0
    detection_rate_pct: float = 0.0
    preview_jpeg: bytes | None = None
    frame_id: int = 0
    status: str = "Starting camera"


class LiveTracker:
    """Reads the webcam on a worker thread and publishes the latest viewer position."""

    def __init__(
        self,
        source: int | Path,
        camera: CameraModel,
        screen: ScreenGeometry,
        model_directory: Path,
        calibration_path: Path,
        reference_distance_mm: float,
        method: str = "mediapipe",
    ) -> None:
        self._source = source
        self._capture: cv2.VideoCapture | None = None
        self._camera = camera
        self._screen = screen
        self._model_directory = model_directory
        self._reference_distance_mm = reference_distance_mm
        self._calibrations = load_calibrations(calibration_path)
        self._filters = tuple(OneEuroFilter() for _ in range(3))
        self._smoothing = True
        self._requested_method = method
        self._calibration_request = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._snapshot = self._initial_snapshot(method)
        self._thread = threading.Thread(target=self._run, name="live-tracker", daemon=True)

    @property
    def reference_distance_mm(self) -> float:
        return self._reference_distance_mm

    def open(self) -> None:
        """Try to open the camera or video file. Call this on the main thread.

        On macOS, OpenCV can only show the camera permission prompt from the main
        thread. The prompt is asynchronous, so if this first attempt fails the
        worker keeps retrying until access is granted.
        """
        self._capture = self._try_open()

    def _try_open(self) -> cv2.VideoCapture | None:
        source = str(self._source) if isinstance(self._source, Path) else self._source
        capture = cv2.VideoCapture(source)
        if isinstance(self._source, int):
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._camera.width_px)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._camera.height_px)
        if capture.isOpened():
            return capture
        capture.release()
        return None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def snapshot(self) -> LiveSnapshot:
        with self._lock:
            return self._snapshot

    def select_method(self, method: str) -> None:
        with self._lock:
            self._requested_method = method

    def set_smoothing(self, enabled: bool) -> None:
        with self._lock:
            self._smoothing = enabled

    def request_calibration(self) -> None:
        """Measure a new baseline from the next frames at the reference distance."""
        with self._lock:
            self._calibration_request = True

    def _initial_snapshot(self, method: str) -> LiveSnapshot:
        if method in self._calibrations:
            return LiveSnapshot(
                method=method,
                calibration_source="benchmark",
                reference_eye_separation_px=self._calibrations[method],
            )
        return LiveSnapshot(
            method=method,
            calibration_source="assumed 63 mm IPD",
            reference_eye_separation_px=fallback_eye_separation_px(
                self._camera, self._reference_distance_mm
            ),
        )

    def _publish(self, snapshot: LiveSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def _run(self) -> None:
        while self._capture is None:
            if isinstance(self._source, Path):
                self._publish(replace(self.snapshot(), status=f"Could not open {self._source}"))
                return
            self._publish(
                replace(
                    self.snapshot(),
                    status=f"Waiting for camera {self._source} (check camera permission)",
                )
            )
            if self._stop.wait(CAMERA_RETRY_S):
                return
            self._capture = self._try_open()
        try:
            self._loop(self._capture)
        finally:
            self._capture.release()

    def _loop(self, capture: cv2.VideoCapture) -> None:
        tracker: Tracker | None = None
        start = time.perf_counter()
        last_timestamp_ms = -1
        frame_times: deque[float] = deque(maxlen=30)
        detections: deque[bool] = deque(maxlen=60)
        calibration_samples: list[float] = []
        state = self.snapshot()
        replay_interval_s = 0.0
        if isinstance(self._source, Path):
            replay_interval_s = 1.0 / (capture.get(cv2.CAP_PROP_FPS) or 30.0)
        try:
            while not self._stop.is_set():
                with self._lock:
                    requested = self._requested_method
                    smoothing = self._smoothing
                    if self._calibration_request:
                        self._calibration_request = False
                        calibration_samples = []
                        state = replace(state, calibration_source="measuring")

                if tracker is None or tracker.name != requested:
                    if tracker is not None:
                        tracker.close()
                    state = replace(
                        self._initial_snapshot(requested), frame_id=state.frame_id
                    )
                    self._publish(replace(state, status=f"Loading {requested}"))
                    tracker = create_tracker(requested, self._model_directory)
                    detections.clear()
                    for axis_filter in self._filters:
                        axis_filter.reset()

                if replay_interval_s:
                    wait_s = replay_interval_s - (time.perf_counter() - (frame_times or [0])[-1])
                    if wait_s > 0:
                        time.sleep(wait_s)
                ok, frame = capture.read()
                if not ok and replay_interval_s:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = capture.read()
                if not ok:
                    state = replace(state, status="Camera returned no frame")
                    self._publish(state)
                    time.sleep(0.05)
                    continue

                now = time.perf_counter()
                frame_times.append(now)
                # MediaPipe's video mode rejects timestamps that do not strictly increase.
                timestamp_ms = max(int((now - start) * 1000), last_timestamp_ms + 1)
                last_timestamp_ms = timestamp_ms

                call_start = time.perf_counter()
                result = tracker.track(frame, timestamp_ms)
                latency_ms = (time.perf_counter() - call_start) * 1000.0
                detections.append(result.detected and result.eyes is not None)

                if state.calibration_source == "measuring":
                    if result.eyes is not None and result.eyes.separation_px > 0:
                        calibration_samples.append(result.eyes.separation_px)
                    if len(calibration_samples) >= CALIBRATION_SAMPLES:
                        state = replace(
                            state,
                            calibration_source="live",
                            reference_eye_separation_px=statistics.median(calibration_samples),
                        )
                        calibration_samples = []

                eye_position = None
                smoothed = state.smoothed_position
                if result.eyes is not None and result.eyes.separation_px > 0:
                    position = estimate_viewer_position(
                        result.eyes,
                        self._camera,
                        DepthCalibration(
                            self._reference_distance_mm, state.reference_eye_separation_px
                        ),
                    )
                    eye_position = camera_to_screen(position, self._screen)
                    if smoothing:
                        smoothed = EyePosition(
                            *(
                                axis_filter(value, now)
                                for axis_filter, value in zip(
                                    self._filters,
                                    (eye_position.x_mm, eye_position.y_mm, eye_position.z_mm),
                                    strict=True,
                                )
                            )
                        )
                    else:
                        smoothed = eye_position

                camera_fps = 0.0
                if len(frame_times) > 1:
                    camera_fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0])

                state = replace(
                    state,
                    detected=eye_position is not None,
                    eyes=result.eyes,
                    eye_position=eye_position,
                    smoothed_position=smoothed,
                    latency_ms=latency_ms,
                    camera_fps=camera_fps,
                    detection_rate_pct=100.0 * sum(detections) / len(detections),
                    preview_jpeg=_encode_preview(frame, result.eyes),
                    frame_id=state.frame_id + 1,
                    status="Tracking" if eye_position is not None else "No face detected",
                )
                self._publish(state)
        finally:
            if tracker is not None:
                tracker.close()


def _encode_preview(frame_bgr: np.ndarray, eyes: EyePair | None) -> bytes | None:
    preview = frame_bgr.copy()
    if eyes is not None:
        midpoint = eyes.midpoint
        points = [(round(p.x), round(p.y)) for p in (eyes.first, eyes.second)]
        cv2.line(preview, points[0], points[1], (233, 135, 57), 2, cv2.LINE_AA)
        for point in points:
            cv2.circle(preview, point, 9, (233, 135, 57), 2, cv2.LINE_AA)
        cv2.drawMarker(
            preview,
            (round(midpoint.x), round(midpoint.y)),
            (12, 163, 12),
            cv2.MARKER_CROSS,
            22,
            2,
            cv2.LINE_AA,
        )
    # Mirror so the preview behaves like a mirror for the person in front of it.
    preview = cv2.flip(preview, 1)
    height, width = preview.shape[:2]
    scale = PREVIEW_WIDTH_PX / width
    preview = cv2.resize(
        preview, (PREVIEW_WIDTH_PX, round(height * scale)), interpolation=cv2.INTER_AREA
    )
    ok, encoded = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return encoded.tobytes() if ok else None
