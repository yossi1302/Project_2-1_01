from pathlib import Path

import pytest

from viewer_tracking.reporting import build_report_fragment, evaluate_methods


def _row(method: str, condition: str, detection: float, latency: float) -> dict[str, str]:
    return {
        "method": method,
        "condition": condition,
        "frames": "100",
        "detection_success_pct": str(detection),
        "latency_median_ms": str(latency / 2.0),
        "latency_p95_ms": str(latency),
        "jitter_x_mm": "1.0",
        "jitter_y_mm": "2.0",
        "jitter_z_mm": "3.0",
        "positional_error_median_mm": "10.0",
    }


def test_evaluation_applies_functional_and_realtime_gates() -> None:
    rows = []
    for method, detection, latency in (
        ("haar", 90.0, 10.0),
        ("yunet", 98.0, 40.0),
        ("mediapipe", 99.0, 20.0),
    ):
        rows.extend(
            _row(method, condition, detection, latency)
            for condition in ("stationary", "horizontal", "distance")
        )

    evaluations = {item.method: item for item in evaluate_methods(rows)}

    assert not evaluations["haar"].passed_gates
    assert not evaluations["yunet"].passed_gates
    assert evaluations["mediapipe"].passed_gates
    assert evaluations["mediapipe"].stationary_jitter_mm == pytest.approx(14**0.5)


def test_report_fragment_names_highest_scoring_passing_method(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    header = (
        "method,condition,frames,detection_success_pct,latency_median_ms,latency_p95_ms,"
        "jitter_x_mm,jitter_y_mm,jitter_z_mm,positional_error_median_mm\n"
    )
    lines = []
    for method, detection, latency in (
        ("haar", 90.0, 10.0),
        ("yunet", 98.0, 25.0),
        ("mediapipe", 99.0, 20.0),
    ):
        for condition in ("stationary", "horizontal", "distance"):
            lines.append(f"{method},{condition},100,{detection},{latency / 2},{latency},1,2,3,10")
    summary.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    output = tmp_path / "results.tex"

    build_report_fragment(summary, output)

    generated = output.read_text(encoding="utf-8")
    assert r"\resultspendingfalse" in generated
    assert "MediaPipe is selected" in generated
