from __future__ import annotations

from typing import Protocol

from oracle.core.models import MetricPoint


class MetricSource(Protocol):
    def read(self) -> list[MetricPoint]:
        ...


class InMemoryMetricSource:
    def __init__(self, points: list[MetricPoint] | None = None) -> None:
        self.points = points or []

    def push(self, point: MetricPoint) -> None:
        self.points.append(point)

    def read(self) -> list[MetricPoint]:
        return list(self.points)
