from __future__ import annotations

from oracle.core.models import Prediction, PredictionAccuracy


class AccuracyCalculator:
    def calculate(self, predictions: list[Prediction], false_negatives: int = 0) -> PredictionAccuracy:
        true_positives = sum(1 for p in predictions if p.status in {"confirmed", "prevented"})
        false_positives = sum(1 for p in predictions if p.status == "false_positive")
        total = len(predictions)
        precision = true_positives / (true_positives + false_positives) if true_positives + false_positives else 0.0
        recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        accuracy = PredictionAccuracy(
            total_predictions=total,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1, 3),
            trend="improving" if precision >= 0.75 and recall >= 0.75 else "needs_data",
        )
        for prediction in predictions:
            self._inc(accuracy.by_service, prediction.affected_service, prediction.status)
            self._inc(accuracy.by_incident_type, prediction.predicted_incident_type, prediction.status)
            self._inc(accuracy.by_time_period, prediction.created_at.date().isoformat(), prediction.status)
        return accuracy

    def _inc(self, bucket: dict[str, dict[str, int]], key: str, status: str) -> None:
        bucket.setdefault(key, {})
        bucket[key][status] = bucket[key].get(status, 0) + 1

