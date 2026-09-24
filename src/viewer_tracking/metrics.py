from __future__ import annotations

import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class FrameMeasurement:
    method: str
    condition: str
    run: int
    frame: int
    timestamp_ms: int
    detected: bool
    latency_ms: float
    eye_midpoint_x_px: float | None
    eye_midpoint_y_px: float | None
    eye_separation_px: float | None
    position_x_mm: float | None
    position_y_mm: float | None
    position_z_mm: float | None
    positional_error_mm: float | None


@dataclass(frozen=True)
class Summary:
    method: str
    condition: str
    frames: int
    detection_success_pct: float
    latency_median_ms: float
    latency_p95_ms: float
    jitter_x_mm: float | None
    jitter_y_mm: float | None
    jitter_z_mm: float | None
    positional_error_median_mm: float | None


def summarise(measurements: Iterable[FrameMeasurement]) -> Summary:
    rows = list(measurements)
    if not rows:
        raise ValueError("At least one frame measurement is required")
    method = rows[0].method
    condition = rows[0].condition
    if any(row.method != method or row.condition != condition for row in rows):
        raise ValueError("A summary may contain only one method and condition")

    detected = [row for row in rows if row.detected]
    latency = [row.latency_ms for row in rows]
    errors = [row.positional_error_mm for row in detected if row.positional_error_mm is not None]
    return Summary(
        method=method,
        condition=condition,
        frames=len(rows),
        detection_success_pct=100.0 * len(detected) / len(rows),
        latency_median_ms=statistics.median(latency),
        latency_p95_ms=_percentile(latency, 95.0),
        jitter_x_mm=_sample_std(row.position_x_mm for row in detected),
        jitter_y_mm=_sample_std(row.position_y_mm for row in detected),
        jitter_z_mm=_sample_std(row.position_z_mm for row in detected),
        positional_error_median_mm=statistics.median(errors) if errors else None,
    )


def euclidean_error(
    actual: tuple[float, float, float],
    expected: tuple[float, float, float],
) -> float:
    return math.sqrt(sum((a - e) ** 2 for a, e in zip(actual, expected, strict=True)))


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("Percentile requires at least one value")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _sample_std(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return statistics.stdev(present) if len(present) >= 2 else None
