import pytest

from viewer_tracking.metrics import FrameMeasurement, euclidean_error, summarise


def _measurement(frame: int, detected: bool, latency: float, x: float | None) -> FrameMeasurement:
    return FrameMeasurement(
        method="test",
        condition="stationary",
        run=1,
        frame=frame,
        timestamp_ms=frame * 33,
        detected=detected,
        latency_ms=latency,
        eye_midpoint_x_px=None,
        eye_midpoint_y_px=None,
        eye_separation_px=None,
        position_x_mm=x,
        position_y_mm=0.0 if detected else None,
        position_z_mm=600.0 if detected else None,
        positional_error_mm=2.0 if detected else None,
    )


def test_summary_uses_all_frames_for_detection_and_latency() -> None:
    summary = summarise(
        [
            _measurement(0, True, 10.0, 0.0),
            _measurement(1, False, 20.0, None),
            _measurement(2, True, 30.0, 2.0),
        ]
    )

    assert summary.frames == 3
    assert summary.detection_success_pct == pytest.approx(66.6667, rel=1e-4)
    assert summary.latency_median_ms == 20.0
    assert summary.latency_p95_ms == pytest.approx(29.0)
    assert summary.jitter_x_mm == pytest.approx(2**0.5)
    assert summary.positional_error_median_mm == 2.0


def test_euclidean_error_is_three_dimensional() -> None:
    assert euclidean_error((1.0, 2.0, 3.0), (4.0, 6.0, 3.0)) == 5.0
