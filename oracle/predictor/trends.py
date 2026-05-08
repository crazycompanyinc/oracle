from __future__ import annotations

from oracle.core.models import MetricPoint


class TrendAnalyzer:
    def slope(self, points: list[MetricPoint]) -> float:
        ordered = sorted(points, key=lambda p: p.timestamp)
        if len(ordered) < 2:
            return 0.0
        first, last = ordered[0], ordered[-1]
        minutes = max((last.timestamp - first.timestamp).total_seconds() / 60, 1)
        return (last.value - first.value) / minutes

    def minutes_to_threshold(self, points: list[MetricPoint], threshold: float) -> float | None:
        ordered = sorted(points, key=lambda p: p.timestamp)
        if len(ordered) < 2:
            return None
        rate = self.slope(ordered)
        if rate <= 0:
            return None
        remaining = threshold - ordered[-1].value
        if remaining <= 0:
            return 0.0
        return remaining / rate

    def score(self, points: list[MetricPoint], threshold: float, horizon_minutes: int = 60) -> float:
        eta = self.minutes_to_threshold(points, threshold)
        if eta is None or eta > horizon_minutes:
            return 0.0
        return max(0.0, min(1.0, 1 - eta / horizon_minutes))

