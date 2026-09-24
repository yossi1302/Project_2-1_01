from __future__ import annotations

import csv
import statistics
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2

from .config import CalibrationSegment, ExperimentConfig, TestCondition
from .geometry import DepthCalibration, estimate_viewer_position
from .metrics import FrameMeasurement, Summary, euclidean_error, summarise
from .trackers import create_tracker

METHODS = ("haar", "yunet", "mediapipe")


@dataclass(frozen=True)
class CalibrationResult:
    method: str
    reference_distance_mm: float
    reference_eye_separation_px: float
    detected_frames: int
    total_frames: int


def run_experiment(
    config: ExperimentConfig,
    model_directory: Path,
    output_directory: Path,
    methods: tuple[str, ...] = METHODS,
) -> tuple[Path, Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    measurements: list[FrameMeasurement] = []
    calibration_results: list[CalibrationResult] = []
    _require_video(config.recording_video)

    for method in methods:
        tracker = create_tracker(method, model_directory)
        try:
            calibration, calibration_result = _calibrate(
                tracker,
                method,
                config.recording_video,
                config.calibration,
                config.fps,
            )
        finally:
            tracker.close()
        calibration_results.append(calibration_result)

        for condition in config.conditions:
            for run_number in range(1, config.runs + 1):
                tracker = create_tracker(method, model_directory)
                try:
                    measurements.extend(
                        _run_video(
                            tracker,
                            method,
                            condition,
                            run_number,
                            config,
                            calibration,
                        )
                    )
                finally:
                    tracker.close()

    calibration_path = output_directory / "calibration.csv"
    _write_dataclasses(calibration_path, calibration_results)
    frame_path = output_directory / "frame_measurements.csv"
    _write_dataclasses(frame_path, measurements)

    grouped: dict[tuple[str, str], list[FrameMeasurement]] = defaultdict(list)
    for measurement in measurements:
        grouped[(measurement.method, measurement.condition)].append(measurement)
    summaries = [summarise(rows) for rows in grouped.values()]
    summary_path = output_directory / "summary.csv"
    _write_dataclasses(summary_path, summaries)
    return calibration_path, frame_path, summary_path


def _calibrate(
    tracker,
    method: str,
    video: Path,
    segment: CalibrationSegment,
    fallback_fps: float,
) -> tuple[DepthCalibration, CalibrationResult]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open calibration video: {video}")
    fps = capture.get(cv2.CAP_PROP_FPS) or fallback_fps
    separations: list[float] = []
    source_frame_index = 0
    calibration_frame_count = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        timestamp_ms = round(source_frame_index * 1000.0 / fps)
        timestamp_seconds = timestamp_ms / 1000.0
        source_frame_index += 1
        if timestamp_seconds < segment.start_seconds:
            continue
        if timestamp_seconds >= segment.end_seconds:
            break
        result = tracker.track(frame, timestamp_ms)
        if result.detected and result.eyes is not None:
            separations.append(result.eyes.separation_px)
        calibration_frame_count += 1
    capture.release()

    minimum_detected_frames = 10
    if len(separations) < minimum_detected_frames:
        raise RuntimeError(
            f"Calibration failed for {method}: detected both eyes in "
            f"{len(separations)} of {calibration_frame_count} frames; at least "
            f"{minimum_detected_frames} are required."
        )
    reference_eye_separation_px = statistics.median(separations)
    calibration = DepthCalibration(
        reference_distance_mm=segment.reference_distance_mm,
        reference_eye_separation_px=reference_eye_separation_px,
    )
    result = CalibrationResult(
        method=method,
        reference_distance_mm=segment.reference_distance_mm,
        reference_eye_separation_px=reference_eye_separation_px,
        detected_frames=len(separations),
        total_frames=calibration_frame_count,
    )
    return calibration, result


def _run_video(
    tracker,
    method: str,
    condition: TestCondition,
    run_number: int,
    config: ExperimentConfig,
    calibration: DepthCalibration,
) -> list[FrameMeasurement]:
    capture = cv2.VideoCapture(str(config.recording_video))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {config.recording_video}")
    fps = capture.get(cv2.CAP_PROP_FPS) or config.fps
    rows: list[FrameMeasurement] = []
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        timestamp_ms = round(frame_index * 1000.0 / fps)
        timestamp_seconds = timestamp_ms / 1000.0
        if timestamp_seconds < condition.start_seconds:
            frame_index += 1
            continue
        if timestamp_seconds >= condition.end_seconds:
            break
        started = time.perf_counter_ns()
        result = tracker.track(frame, timestamp_ms)
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000.0

        midpoint_x = midpoint_y = separation = None
        x_mm = y_mm = z_mm = error_mm = None
        if result.detected and result.eyes is not None:
            midpoint = result.eyes.midpoint
            position = estimate_viewer_position(result.eyes, config.camera, calibration)
            midpoint_x, midpoint_y = midpoint.x, midpoint.y
            separation = result.eyes.separation_px
            x_mm, y_mm, z_mm = position.x_mm, position.y_mm, position.z_mm
            if condition.expected_position is not None:
                expected = condition.expected_position
                error_mm = euclidean_error(
                    (x_mm, y_mm, z_mm),
                    (expected.x_mm, expected.y_mm, expected.z_mm),
                )

        rows.append(
            FrameMeasurement(
                method=method,
                condition=condition.name,
                run=run_number,
                frame=frame_index,
                timestamp_ms=timestamp_ms,
                detected=result.detected,
                latency_ms=latency_ms,
                eye_midpoint_x_px=midpoint_x,
                eye_midpoint_y_px=midpoint_y,
                eye_separation_px=separation,
                position_x_mm=x_mm,
                position_y_mm=y_mm,
                position_z_mm=z_mm,
                positional_error_mm=error_mm,
            )
        )
        frame_index += 1
    capture.release()
    if not rows:
        raise RuntimeError(
            f"Video contains no frames for condition '{condition.name}': {config.recording_video}"
        )
    return rows


def _require_video(video: Path) -> None:
    if not video.exists():
        raise FileNotFoundError(
            f"Missing experiment video: {video}. Record the guided session before "
            "running the benchmark."
        )


def _write_dataclasses(
    path: Path,
    rows: list[CalibrationResult] | list[FrameMeasurement] | list[Summary],
) -> None:
    if not rows:
        raise ValueError("Cannot write an empty result file")
    dictionaries = [asdict(row) for row in rows]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=dictionaries[0].keys())
        writer.writeheader()
        writer.writerows(dictionaries)
