"""Keep recent tracking results for the live metrics panel."""

from collections import deque
from dataclasses import dataclass
import math
import statistics


@dataclass(frozen=True)
class MetricsSnapshot:
    status: str
    samples: int
    detected: int
    fps: float
    detection_pct: float | None
    median_ms: float | None
    p95_ms: float | None
    last_seen_seconds: float | None
    position_cm: tuple[float, float, float] | None
    separation_px: float | None


class TrackingMetrics:
    def __init__(self, started_at, window_seconds=5.0, stale_seconds=1.0):
        if window_seconds <= 0 or stale_seconds <= 0:
            raise ValueError("Window and stale durations must be positive")
        self.started_at = started_at
        self.window_seconds = window_seconds
        self.stale_seconds = stale_seconds
        self._samples = deque()
        self._last_completed = None
        self._last_seen = None
        self._position = None
        self._separation = None
        self._detected = False
        self._error = None

    def record(self, completed_at, latency_ms, position_cm=None, separation_px=None):
        """Include successful and missed calls; invalid positions count as misses."""
        if not math.isfinite(latency_ms) or latency_ms < 0:
            raise ValueError("Latency must be finite and non-negative")
        detected = (
            position_cm is not None
            and len(position_cm) == 3
            and all(math.isfinite(value) for value in position_cm)
            and separation_px is not None
            and math.isfinite(separation_px)
            and separation_px > 0
        )
        self._samples.append((completed_at, latency_ms, detected))
        self._last_completed = completed_at
        self._detected = detected
        self._error = None
        if detected:
            self._last_seen = completed_at
            self._position = tuple(position_cm)
            self._separation = separation_px
        self._prune(completed_at)

    def unavailable(self, reason):
        # No frame means no detector call, so don't count it as a missed detection.
        self._error = reason

    def _prune(self, now):
        while self._samples and self._samples[0][0] <= now - self.window_seconds:
            self._samples.popleft()

    def snapshot(self, now):
        self._prune(now)
        times = sorted(sample[1] for sample in self._samples)
        count = len(times)
        detected = sum(sample[2] for sample in self._samples)
        elapsed = min(self.window_seconds, max(0.0, now - self.started_at))
        age = None if self._last_seen is None else max(0.0, now - self._last_seen)
        fresh = (
            self._last_completed is not None
            and now - self._last_completed <= self.stale_seconds
        )
        if self._error:
            status = self._error
        elif self._last_completed is None:
            status = "Waiting for camera"
        elif not fresh:
            status = "No recent tracking frames"
        elif self._detected:
            status = "Eyes detected"
        else:
            status = "Eyes not detected"

        p95 = None
        if count:
            rank = 0.95 * (count - 1)
            low, high = math.floor(rank), math.ceil(rank)
            p95 = times[low] + (times[high] - times[low]) * (rank - low)
        show_position = fresh and self._detected and not self._error
        return MetricsSnapshot(
            status=status,
            samples=count,
            detected=detected,
            fps=count / elapsed if elapsed > 0 else 0.0,
            detection_pct=100.0 * detected / count if count else None,
            median_ms=statistics.median(times) if times else None,
            p95_ms=p95,
            last_seen_seconds=age,
            position_cm=self._position if show_position else None,
            separation_px=self._separation if show_position else None,
        )
