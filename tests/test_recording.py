from pathlib import Path

from viewer_tracking.config import load_config
from viewer_tracking.recording import _phase_at


def test_guided_recording_phase_boundaries() -> None:
    config = load_config(Path("config/experiment.toml"))

    assert _phase_at(config, 0.0)[0] == "CALIBRATION"
    assert _phase_at(config, 5.0)[0] == "TEST: stationary"
    assert _phase_at(config, 20.0)[0] == "PREPARE: horizontal"
    assert _phase_at(config, 25.0)[0] == "TEST: horizontal"


def test_all_conditions_share_one_recording() -> None:
    config = load_config(Path("config/experiment.toml"))

    assert config.recording_video == Path("data/private/experiment.mp4")
    assert len(config.conditions) == 8
    assert config.total_recording_seconds == 170.0
