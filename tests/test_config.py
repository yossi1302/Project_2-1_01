from pathlib import Path

from viewer_tracking.config import load_config


def test_project_configuration_loads() -> None:
    config = load_config(Path("config/experiment.toml"))

    assert config.runs == 3
    assert config.camera.width_px == 1280
    assert config.recording_video == Path("data/private/experiment.mp4")
    assert config.calibration.duration_seconds == 5.0
    assert config.calibration.reference_distance_mm == 600.0
    assert config.conditions[0].name == "stationary"
    assert config.conditions[0].start_seconds == 5.0
    assert config.conditions[0].duration_seconds == 15.0
    assert config.conditions[0].expected_position is not None
    assert config.total_recording_seconds == 170.0
