import pytest

from viewer_tracking.geometry import CameraModel, DepthCalibration, estimate_viewer_position
from viewer_tracking.models import EyePair, Point2D


def test_centred_eye_pair_maps_to_camera_axis() -> None:
    camera = CameraModel(width_px=1000, height_px=500, horizontal_fov_deg=90.0)
    eyes = EyePair(Point2D(450.0, 250.0), Point2D(550.0, 250.0))

    calibration = DepthCalibration(600.0, 50.0)
    position = estimate_viewer_position(eyes, camera, calibration)

    assert position.x_mm == pytest.approx(0.0)
    assert position.y_mm == pytest.approx(0.0)
    assert position.z_mm == pytest.approx(300.0)


def test_image_offset_maps_to_lateral_offset() -> None:
    camera = CameraModel(width_px=1000, height_px=500, horizontal_fov_deg=90.0)
    eyes = EyePair(Point2D(550.0, 275.0), Point2D(650.0, 275.0))

    calibration = DepthCalibration(600.0, 50.0)
    position = estimate_viewer_position(eyes, camera, calibration)

    assert position.x_mm == pytest.approx(60.0)
    assert position.y_mm == pytest.approx(15.0)


def test_identical_eye_centres_are_rejected() -> None:
    camera = CameraModel(width_px=1000, height_px=500, horizontal_fov_deg=90.0)
    eyes = EyePair(Point2D(500.0, 250.0), Point2D(500.0, 250.0))

    with pytest.raises(ValueError, match="distinct"):
        estimate_viewer_position(eyes, camera, DepthCalibration(600.0, 50.0))


def test_invalid_calibration_is_rejected() -> None:
    with pytest.raises(ValueError, match="reference distance"):
        DepthCalibration(0.0, 50.0)
