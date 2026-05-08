from __future__ import annotations

from oracle.core.db import OracleDB
from oracle.core.models import Prediction, PredictionAccuracy, utcnow
from oracle.feedback.accuracy import AccuracyCalculator


class PredictionFeedback:
    def __init__(self, db: OracleDB) -> None:
        self.db = db
        self.calculator = AccuracyCalculator()
        self.false_negatives = 0

    def record_outcome(self, prediction_id: str, happened: bool, prevented: bool = False) -> Prediction:
        predictions = self.db.list("predictions")
        prediction = next(p for p in predictions if p.id == prediction_id)
        if prevented:
            prediction.status = "prevented"
        elif happened:
            prediction.status = "confirmed"
        else:
            prediction.status = "false_positive"
            self._penalize_indicators(prediction.leading_indicators)
        prediction.resolved_at = utcnow()
        self.db.update_prediction(prediction)
        return prediction

    def record_missed_incident(self) -> None:
        self.false_negatives += 1

    def accuracy(self) -> PredictionAccuracy:
        return self.calculator.calculate(self.db.list("predictions"), false_negatives=self.false_negatives)

    def _penalize_indicators(self, indicator_names: list[str]) -> None:
        indicators = self.db.list("indicators")
        for indicator in indicators:
            if indicator.name in indicator_names:
                indicator.confidence = round(max(0.05, indicator.confidence * 0.9), 3)
                indicator.false_positive_rate = round(min(1.0, indicator.false_positive_rate + 0.05), 3)
        self.db.replace("indicators", indicators)

