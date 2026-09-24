from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .geometry import CameraModel
from .models import ViewerPosition


@dataclass(frozen=True)
class TestCondition:
    name: str
    instructions: str
    preparation_seconds: float
    start_seconds: float
    duration_seconds: float
    expected_position: ViewerPosition | None

    @property
    def end_seconds(self) -> float:
        return self.start_seconds + self.duration_seconds


@dataclass(frozen=True)
class CalibrationSegment:
    instructions: str
    start_seconds: float
    duration_seconds: float
    reference_distance_mm: float

    @property
    def end_seconds(self) -> float:
        return self.start_seconds + self.duration_seconds


@dataclass(frozen=True)
class ExperimentConfig:
    runs: int
    camera_index: int
    camera: CameraModel
    fps: float
    recording_video: Path
    calibration: CalibrationSegment
    conditions: tuple[TestCondition, ...]

    @property
    def total_recording_seconds(self) -> float:
        return self.conditions[-1].end_seconds


def load_config(path: Path) -> ExperimentConfig:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    experiment = raw["experiment"]
    camera = raw["camera"]
    recording = raw["recording"]
    calibration_raw = raw["calibration"]
    reference_distance_mm = float(calibration_raw["reference_distance_mm"])
    if reference_distance_mm <= 0:
        raise ValueError("Calibration reference distance must be positive")
    calibration_duration_seconds = float(calibration_raw["duration_seconds"])
    if calibration_duration_seconds <= 0:
        raise ValueError("Calibration duration must be positive")
    calibration = CalibrationSegment(
        instructions=str(calibration_raw["instructions"]),
        start_seconds=0.0,
        duration_seconds=calibration_duration_seconds,
        reference_distance_mm=reference_distance_mm,
    )

    conditions: list[TestCondition] = []
    next_start_seconds = calibration.end_seconds
    for item in raw["conditions"]:
        expected_raw = item.get("expected_position_mm")
        expected = None
        if expected_raw is not None:
            expected = ViewerPosition(*map(float, expected_raw))
        preparation_seconds = float(item.get("preparation_seconds", 5.0))
        duration_seconds = float(item.get("duration_seconds", 15.0))
        if preparation_seconds < 0:
            raise ValueError("Condition preparation time cannot be negative")
        if duration_seconds <= 0:
            raise ValueError("Condition duration must be positive")
        start_seconds = next_start_seconds + preparation_seconds
        conditions.append(
            TestCondition(
                name=str(item["name"]),
                instructions=str(item["instructions"]),
                preparation_seconds=preparation_seconds,
                start_seconds=start_seconds,
                duration_seconds=duration_seconds,
                expected_position=expected,
            )
        )
        next_start_seconds = start_seconds + duration_seconds

    if not conditions:
        raise ValueError("At least one test condition is required")

    runs = int(experiment["runs"])
    if runs < 1:
        raise ValueError("Experiment runs must be at least one")
    fps = float(camera["fps"])
    if fps <= 0:
        raise ValueError("Camera FPS must be positive")

    return ExperimentConfig(
        runs=runs,
        camera_index=int(camera["index"]),
        camera=CameraModel(
            width_px=int(camera["width_px"]),
            height_px=int(camera["height_px"]),
            horizontal_fov_deg=float(camera["horizontal_fov_deg"]),
        ),
        fps=fps,
        recording_video=Path(recording["video"]),
        calibration=calibration,
        conditions=tuple(conditions),
    )
