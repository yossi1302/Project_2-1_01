from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float


@dataclass(frozen=True)
class EyePair:
    first: Point2D
    second: Point2D

    @property
    def midpoint(self) -> Point2D:
        return Point2D(
            x=(self.first.x + self.second.x) / 2.0,
            y=(self.first.y + self.second.y) / 2.0,
        )

    @property
    def separation_px(self) -> float:
        return ((self.second.x - self.first.x) ** 2 + (self.second.y - self.first.y) ** 2) ** 0.5


@dataclass(frozen=True)
class ViewerPosition:
    x_mm: float
    y_mm: float
    z_mm: float


@dataclass(frozen=True)
class TrackingResult:
    detected: bool
    eyes: EyePair | None = None
    confidence: float | None = None

    @classmethod
    def missed(cls) -> TrackingResult:
        return cls(detected=False)
