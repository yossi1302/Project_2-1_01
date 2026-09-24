from __future__ import annotations

import math
from dataclasses import dataclass

from .models import EyePair, ViewerPosition


@dataclass(frozen=True)
class CameraModel:
    width_px: int
    height_px: int
    horizontal_fov_deg: float

    def __post_init__(self) -> None:
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("Camera dimensions must be positive")
        if not 1.0 < self.horizontal_fov_deg < 179.0:
            raise ValueError("Horizontal field of view must be between 1 and 179 degrees")

    @property
    def focal_length_px(self) -> float:
        half_angle = math.radians(self.horizontal_fov_deg) / 2.0
        return self.width_px / (2.0 * math.tan(half_angle))

    @property
    def principal_point(self) -> tuple[float, float]:
        return self.width_px / 2.0, self.height_px / 2.0


@dataclass(frozen=True)
class DepthCalibration:
    reference_distance_mm: float
    reference_eye_separation_px: float

    def __post_init__(self) -> None:
        if self.reference_distance_mm <= 0:
            raise ValueError("Calibration reference distance must be positive")
        if self.reference_eye_separation_px <= 0:
            raise ValueError("Calibration eye separation must be positive")


def estimate_viewer_position(
    eyes: EyePair,
    camera: CameraModel,
    calibration: DepthCalibration,
) -> ViewerPosition:
    """Estimate the eye midpoint in camera coordinates with a pinhole model.

    Positive x points right in the image, positive y points down, and positive z
    points away from the camera. The estimate assumes the eye line is close to
    parallel with the image plane.
    """
    if eyes.separation_px <= 0:
        raise ValueError("Detected eye centres must be distinct")

    focal = camera.focal_length_px
    z_mm = (
        calibration.reference_distance_mm
        * calibration.reference_eye_separation_px
        / eyes.separation_px
    )
    centre_x, centre_y = camera.principal_point
    midpoint = eyes.midpoint
    return ViewerPosition(
        x_mm=(midpoint.x - centre_x) * z_mm / focal,
        y_mm=(midpoint.y - centre_y) * z_mm / focal,
        z_mm=z_mm,
    )
