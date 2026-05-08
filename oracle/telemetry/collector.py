from __future__ import annotations

from oracle.core.db import OracleDB
from oracle.core.models import MetricPoint
from oracle.telemetry.sources import MetricSource


class MetricsCollector:
    def __init__(self, db: OracleDB, sources: list[MetricSource] | None = None) -> None:
        self.db = db
        self.sources = sources or []

    def add_source(self, source: MetricSource) -> None:
        self.sources.append(source)

    def ingest(self, points: list[MetricPoint]) -> list[MetricPoint]:
        for point in points:
            self.db.add("metrics", point)
        return points

    def collect(self) -> list[MetricPoint]:
        points: list[MetricPoint] = []
        for source in self.sources:
            points.extend(source.read())
        return self.ingest(points)

