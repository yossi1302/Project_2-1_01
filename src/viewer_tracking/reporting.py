from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

NORMAL_CONDITIONS = ("stationary", "horizontal", "distance")
ADVERSE_CONDITIONS = ("low_light", "glasses", "occlusion", "head_rotation")
WEIGHTS = {
    "detection": 0.30,
    "latency": 0.25,
    "jitter": 0.20,
    "error": 0.15,
    "robustness": 0.05,
    "cost": 0.05,
}
IMPLEMENTATION_COST = {"haar": 100.0, "yunet": 50.0, "mediapipe": 0.0}


@dataclass(frozen=True)
class MethodEvaluation:
    method: str
    detection_pct: float
    p95_latency_ms: float
    stationary_jitter_mm: float | None
    positional_error_mm: float | None
    passed_gates: bool
    weighted_score: float


def build_report_fragment(summary_csv: Path, output_path: Path) -> Path:
    rows = _read_rows(summary_csv)
    evaluations = evaluate_methods(rows)
    passing = [item for item in evaluations if item.passed_gates]
    if passing:
        selected = max(passing, key=lambda item: item.weighted_score)
        reason = (
            f"{_display(selected.method)} is selected for phases 2 and 3. It passed both "
            f"predefined gates and achieved the highest weighted score "
            f"({selected.weighted_score:.1f}/100) among the passing methods."
        )
        other_passing = sorted(
            (item for item in passing if item.method != selected.method),
            key=lambda item: item.weighted_score,
            reverse=True,
        )
        if other_passing:
            runner_up = other_passing[0]
            reason += (
                f" {_display(runner_up.method)} also passed, but its worst normal-condition "
                f"P95 latency was {runner_up.p95_latency_ms:.1f} ms versus "
                f"{selected.p95_latency_ms:.1f} ms for {_display(selected.method)}"
            )
            if (
                runner_up.stationary_jitter_mm is not None
                and selected.stationary_jitter_mm is not None
            ):
                reason += (
                    f", and its stationary 3D jitter was "
                    f"{runner_up.stationary_jitter_mm:.1f} mm versus "
                    f"{selected.stationary_jitter_mm:.1f} mm"
                )
            reason += "."
        failed = [item for item in evaluations if not item.passed_gates]
        for item in failed:
            failures: list[str] = []
            condition_rows = {row["condition"]: row for row in rows if row["method"] == item.method}
            low_detection = [
                name
                for name in NORMAL_CONDITIONS
                if float(condition_rows[name]["detection_success_pct"]) < 95.0
            ]
            if low_detection:
                failures.append("sub-95% detection in " + ", ".join(low_detection))
            if item.p95_latency_ms >= 33.3:
                failures.append(f"{item.p95_latency_ms:.1f} ms worst-case P95 latency")
            reason += (
                f" {_display(item.method)} was excluded because it had "
                + " and ".join(failures)
                + "."
            )
    else:
        selected = max(evaluations, key=lambda item: item.detection_pct)
        reason = (
            "No method passed both predefined gates. "
            f"{_display(selected.method)} is the provisional phase-2 fallback because it had "
            "the highest normal-condition detection success. The team must test reduced input "
            "resolution and asynchronous capture before freezing the phase-3 implementation."
        )

    lines = [
        "% Generated from measured summary.csv. Do not edit by hand.",
        r"\newif\ifresultspending",
        r"\resultspendingfalse",
        "",
        r"\newcommand{\ResultTable}{%",
        r"\begin{tabularx}{\columnwidth}{@{}lrrrr@{}}",
        r"\toprule",
        r"Method & Detect. & P95 ms & Jitter mm & Score\\",
        r"\midrule",
    ]
    for item in evaluations:
        jitter = "--" if item.stationary_jitter_mm is None else f"{item.stationary_jitter_mm:.1f}"
        lines.append(
            f"{_display(item.method)} & {item.detection_pct:.1f}\\% & "
            f"{item.p95_latency_ms:.1f} & {jitter} & {item.weighted_score:.1f}\\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}}",
            "",
            r"\newcommand{\SelectionStatement}{" + _escape_latex(reason) + "}",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def evaluate_methods(rows: list[dict[str, str]]) -> list[MethodEvaluation]:
    methods = sorted({row["method"] for row in rows})
    by_method_condition = {(row["method"], row["condition"]): row for row in rows}
    raw: dict[str, dict[str, float | None]] = {}
    for method in methods:
        normal = [by_method_condition[(method, name)] for name in NORMAL_CONDITIONS]
        detection = _mean(float(row["detection_success_pct"]) for row in normal)
        latency = max(float(row["latency_p95_ms"]) for row in normal)
        stationary = by_method_condition[(method, "stationary")]
        jitter_parts = [
            _optional_float(stationary[key])
            for key in ("jitter_x_mm", "jitter_y_mm", "jitter_z_mm")
        ]
        jitter = None
        if all(value is not None for value in jitter_parts):
            jitter = math.sqrt(sum(value**2 for value in jitter_parts if value is not None))
        error = _optional_float(stationary["positional_error_median_mm"])
        adverse = [
            float(by_method_condition[(method, name)]["detection_success_pct"])
            for name in ADVERSE_CONDITIONS
            if (method, name) in by_method_condition
        ]
        robustness = (
            min(100.0, 100.0 * _mean(adverse) / detection) if adverse and detection else 0.0
        )
        raw[method] = {
            "detection": detection,
            "latency": latency,
            "jitter": jitter,
            "error": error,
            "robustness": robustness,
            "cost": IMPLEMENTATION_COST.get(method, 0.0),
        }

    scores: dict[str, dict[str, float]] = {method: {} for method in methods}
    for criterion in ("detection", "latency", "jitter", "error", "robustness"):
        available = {
            method: value for method in methods if (value := raw[method][criterion]) is not None
        }
        higher_is_better = criterion in {"detection", "robustness"}
        normalised = _normalise(available, higher_is_better)
        for method in methods:
            scores[method][criterion] = normalised.get(method, 0.0)
    for method in methods:
        scores[method]["cost"] = float(raw[method]["cost"] or 0.0)

    return [
        MethodEvaluation(
            method=method,
            detection_pct=float(raw[method]["detection"] or 0.0),
            p95_latency_ms=float(raw[method]["latency"] or 0.0),
            stationary_jitter_mm=_as_optional(raw[method]["jitter"]),
            positional_error_mm=_as_optional(raw[method]["error"]),
            passed_gates=(
                all(
                    float(by_method_condition[(method, name)]["detection_success_pct"]) >= 95.0
                    for name in NORMAL_CONDITIONS
                )
                and float(raw[method]["latency"] or math.inf) < 33.3
            ),
            weighted_score=sum(scores[method][key] * weight for key, weight in WEIGHTS.items()),
        )
        for method in methods
    ]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No results found in {path}")
    required = {
        (method, condition)
        for method in {row["method"] for row in rows}
        for condition in NORMAL_CONDITIONS
    }
    present = {(row["method"], row["condition"]) for row in rows}
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"Missing required method/condition summaries: {missing}")
    return rows


def _normalise(values: dict[str, float | None], higher_is_better: bool) -> dict[str, float]:
    numeric = {key: float(value) for key, value in values.items() if value is not None}
    if not numeric:
        return {}
    low, high = min(numeric.values()), max(numeric.values())
    if math.isclose(low, high):
        return {key: 100.0 for key in numeric}
    if higher_is_better:
        return {key: 100.0 * (value - low) / (high - low) for key, value in numeric.items()}
    return {key: 100.0 * (high - value) / (high - low) for key, value in numeric.items()}


def _optional_float(value: str) -> float | None:
    return None if value in {"", "None"} else float(value)


def _as_optional(value: float | None) -> float | None:
    return None if value is None else float(value)


def _mean(values) -> float:
    items = list(values)
    return sum(items) / len(items)


def _display(method: str) -> str:
    return {"haar": "Haar", "yunet": "YuNet", "mediapipe": "MediaPipe"}.get(method, method)


def _escape_latex(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )
