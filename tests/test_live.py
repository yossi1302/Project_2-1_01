from pathlib import Path

import pytest

from viewer_tracking.geometry import CameraModel
from viewer_tracking.live import (
    OneEuroFilter,
    ScreenGeometry,
    camera_to_screen,
    fallback_eye_separation_px,
    load_calibrations,
)
from viewer_tracking.models import ViewerPosition


def test_viewer_on_camera_axis_sits_above_screen_centre() -> None:
    screen = ScreenGeometry(width_mm=300.0, height_mm=200.0, camera_above_top_mm=10.0)

    eye = camera_to_screen(ViewerPosition(0.0, 0.0, 600.0), screen)

    assert eye.x_mm == pytest.approx(0.0)
    assert eye.y_mm == pytest.approx(110.0)
    assert eye.z_mm == pytest.approx(600.0)


def test_camera_axes_are_mirrored_into_viewer_axes() -> None:
    screen = ScreenGeometry(width_mm=300.0, height_mm=200.0, camera_above_top_mm=10.0)

    # Image right and down are the viewer's left and down.
    eye = camera_to_screen(ViewerPosition(40.0, 30.0, 500.0), screen)

    assert eye.x_mm == pytest.approx(-40.0)
    assert eye.y_mm == pytest.approx(80.0)


def test_one_euro_filter_passes_first_sample_and_smooths_jumps() -> None:
    smoother = OneEuroFilter(min_cutoff_hz=1.0, beta=0.0)

    assert smoother(10.0, 0.0) == 10.0
    smoothed = smoother(20.0, 1.0 / 30.0)

    assert 10.0 < smoothed < 20.0


def test_one_euro_filter_converges_on_constant_input() -> None:
    smoother = OneEuroFilter()
    value = 0.0
    for frame in range(300):
        value = smoother(100.0 if frame else 0.0, frame / 30.0)

    assert value == pytest.approx(100.0, abs=0.01)


def test_one_euro_filter_follows_fast_motion_more_closely() -> None:
    def lag(beta: float) -> float:
        smoother = OneEuroFilter(min_cutoff_hz=1.0, beta=beta)
        value = 0.0
        for frame in range(30):
            value = smoother(frame * 10.0, frame / 30.0)
        return 290.0 - value

    assert lag(beta=0.05) < lag(beta=0.0)


def test_calibrations_are_read_per_method(tmp_path: Path) -> None:
    path = tmp_path / "calibration.csv"
    path.write_text(
        "method,reference_distance_mm,reference_eye_separation_px,detected_frames,total_frames\n"
        "yunet,600.0,111.9,150,150\n"
        "mediapipe,600.0,105.6,150,150\n"
    )

    assert load_calibrations(path) == {"yunet": 111.9, "mediapipe": 105.6}
    assert load_calibrations(tmp_path / "missing.csv") == {}


def test_fallback_separation_uses_pinhole_projection() -> None:
    camera = CameraModel(width_px=1000, height_px=500, horizontal_fov_deg=90.0)

    # Focal length 500 px, so 63 mm at 600 mm projects to 52.5 px.
    assert fallback_eye_separation_px(camera, 600.0) == pytest.approx(52.5)
