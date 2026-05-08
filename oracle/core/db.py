from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, TypeVar

from oracle.core.models import Incident, LeadingIndicator, MetricPoint, Prediction, PreventionAction

T = TypeVar("T")


class OracleDB:
    """Small JSON-backed repository suitable for local demos and tests."""

    collections = {
        "incidents": Incident,
        "indicators": LeadingIndicator,
        "metrics": MetricPoint,
        "predictions": Prediction,
        "actions": PreventionAction,
    }

    def __init__(self, root: str | Path = ".oracle") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        for name in self.collections:
            self._path(name).touch(exist_ok=True)
            if not self._path(name).read_text().strip():
                self._path(name).write_text("[]\n")

    def _path(self, collection: str) -> Path:
        return self.root / f"{collection}.json"

    def _read_raw(self, collection: str) -> list[dict]:
        return json.loads(self._path(collection).read_text())

    def _write_raw(self, collection: str, rows: Iterable[dict]) -> None:
        self._path(collection).write_text(json.dumps(list(rows), indent=2, sort_keys=True) + "\n")

    def add(self, collection: str, item: T) -> T:
        rows = self._read_raw(collection)
        rows.append(item.to_dict())  # type: ignore[attr-defined]
        self._write_raw(collection, rows)
        return item

    def list(self, collection: str) -> list:
        cls = self.collections[collection]
        return [cls.from_dict(row) for row in self._read_raw(collection)]

    def replace(self, collection: str, items: Iterable) -> None:
        self._write_raw(collection, [item.to_dict() for item in items])

    def update_prediction(self, prediction: Prediction) -> None:
        predictions = [p for p in self.list("predictions") if p.id != prediction.id]
        predictions.append(prediction)
        self.replace("predictions", predictions)

    def clear(self) -> None:
        for collection in self.collections:
            self._write_raw(collection, [])

