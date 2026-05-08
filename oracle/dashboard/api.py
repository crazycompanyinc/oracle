from __future__ import annotations

from oracle.core.db import OracleDB
from oracle.feedback.feedback import PredictionFeedback


class DashboardAPI:
    def __init__(self, db: OracleDB) -> None:
        self.db = db

    def snapshot(self) -> dict:
        return {
            "predictions": [p.to_dict() for p in self.db.list("predictions")],
            "actions": [a.to_dict() for a in self.db.list("actions")],
            "accuracy": PredictionFeedback(self.db).accuracy().to_dict(),
            "indicators": [i.to_dict() for i in self.db.list("indicators")],
        }

