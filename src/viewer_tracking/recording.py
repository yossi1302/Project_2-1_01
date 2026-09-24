from __future__ import annotations

import time
from pathlib import Path

import cv2

from .config import ExperimentConfig


def record_session(
    config: ExperimentConfig,
    camera_index: int | None = None,
) -> Path:
    config.recording_video.parent.mkdir(parents=True, exist_ok=True)
    selected_camera_index = config.camera_index if camera_index is None else camera_index
    if selected_camera_index < 0:
        raise ValueError("Camera index cannot be negative")

    capture = cv2.VideoCapture(selected_camera_index)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera.width_px)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera.height_px)
    capture.set(cv2.CAP_PROP_FPS, config.fps)
    if not capture.isOpened():
        raise RuntimeError(
            f"Could not open camera index {selected_camera_index}. Grant camera access "
            "to the terminal, or try another value with --camera-index."
        )

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(
        str(config.recording_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        config.fps,
        (width, height),
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Could not create video file: {config.recording_video}")

    print(f"Camera index: {selected_camera_index}")
    print(f"One guided recording: {config.total_recording_seconds:.0f} seconds")
    print("Follow the instruction shown in the preview. Preparation frames are not tested.")
    print("Recording starts in 3 seconds. Press q to stop early.")
    time.sleep(3)

    target_frames = round(config.total_recording_seconds * config.fps)
    frame_index = 0
    stopped_early = False
    try:
        while frame_index < target_frames:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("Camera stopped returning frames")
            elapsed = frame_index / config.fps
            label, instruction, phase_end, color = _phase_at(config, elapsed)
            writer.write(frame)

            preview = frame.copy()
            remaining = max(0.0, phase_end - elapsed)
            cv2.putText(
                preview,
                f"{label}  {remaining:04.1f}s",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                color,
                2,
            )
            cv2.putText(
                preview,
                instruction,
                (20, 76),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )
            cv2.imshow("Viewer-position test recorder", preview)
            frame_index += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                stopped_early = True
                break
    finally:
        capture.release()
        writer.release()
        cv2.destroyAllWindows()

    if stopped_early:
        raise RuntimeError(
            f"Recording stopped early after {frame_index / config.fps:.1f} seconds. "
            "Run the record command again to replace the incomplete session."
        )
    return config.recording_video


def _phase_at(
    config: ExperimentConfig,
    elapsed_seconds: float,
) -> tuple[str, str, float, tuple[int, int, int]]:
    calibration = config.calibration
    if elapsed_seconds < calibration.end_seconds:
        return (
            "CALIBRATION",
            calibration.instructions,
            calibration.end_seconds,
            (0, 255, 0),
        )

    for condition in config.conditions:
        if elapsed_seconds < condition.start_seconds:
            return (
                f"PREPARE: {condition.name}",
                condition.instructions,
                condition.start_seconds,
                (0, 255, 255),
            )
        if elapsed_seconds < condition.end_seconds:
            return (
                f"TEST: {condition.name}",
                condition.instructions,
                condition.end_seconds,
                (0, 255, 0),
            )

    return (
        "COMPLETE",
        "Recording complete",
        config.total_recording_seconds,
        (0, 255, 0),
    )
