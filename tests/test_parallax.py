import pytest

from viewer_tracking.live import EyePosition, ScreenGeometry
from viewer_tracking.parallax import off_axis_view

SCREEN = ScreenGeometry(width_mm=300.0, height_mm=200.0)


def _project(view, point: tuple[float, float, float]) -> tuple[float, float]:
    """Project a scene point to normalised film coordinates in [-1, 1]."""
    cx, cy, cz = view.camera_position
    x, y, z = point[0] - cx, point[1] - cy, point[2] - cz
    film_x = x * view.focal_length / y - view.film_offset[0]
    film_z = z * view.focal_length / y - view.film_offset[1]
    return film_x / (view.film_size[0] / 2), film_z / (view.film_size[1] / 2)


@pytest.mark.parametrize(
    "eye",
    [
        EyePosition(0.0, 0.0, 600.0),
        EyePosition(-200.0, 60.0, 500.0),
        EyePosition(150.0, -80.0, 350.0),
    ],
)
def test_screen_corners_fill_the_frame_from_any_eye_position(eye: EyePosition) -> None:
    view = off_axis_view(eye, SCREEN)

    assert _project(view, (-15.0, 0.0, -10.0)) == pytest.approx((-1.0, -1.0))
    assert _project(view, (15.0, 0.0, 10.0)) == pytest.approx((1.0, 1.0))


def test_camera_sits_at_eye_in_centimetres() -> None:
    view = off_axis_view(EyePosition(-200.0, 60.0, 500.0), SCREEN)

    assert view.camera_position == pytest.approx((-20.0, -50.0, 6.0))
    assert view.focal_length == pytest.approx(50.0)


def test_gain_scales_lateral_motion_only() -> None:
    view = off_axis_view(EyePosition(100.0, 50.0, 600.0), SCREEN, gain=2.0)

    assert view.camera_position == pytest.approx((20.0, -60.0, 10.0))


def test_eye_distance_is_clamped_near_the_screen() -> None:
    view = off_axis_view(EyePosition(0.0, 0.0, 20.0), SCREEN)

    assert view.focal_length == pytest.approx(15.0)
