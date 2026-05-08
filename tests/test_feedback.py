from __future__ import annotations

from oracle.core.models import Prediction
from oracle.feedback.accuracy import AccuracyCalculator
from oracle.feedback.feedback import PredictionFeedback


def test_feedback_records_confirmed(db):
    prediction = Prediction("outage", "api", 0.8, "soon", [], [], [])
    db.add("predictions", prediction)
    updated = PredictionFeedback(db).record_outcome(prediction.id, happened=True)
    assert updated.status == "confirmed"


def test_feedback_records_prevented(db):
    prediction = Prediction("outage", "api", 0.8, "soon", [], [], [])
    db.add("predictions", prediction)
    updated = PredictionFeedback(db).record_outcome(prediction.id, happened=True, prevented=True)
    assert updated.status == "prevented"


def test_feedback_records_false_positive(db):
    prediction = Prediction("outage", "api", 0.8, "soon", [], [], ["cpu high"])
    db.add("predictions", prediction)
    updated = PredictionFeedback(db).record_outcome(prediction.id, happened=False)
    assert updated.status == "false_positive"


def test_feedback_penalizes_indicator(db):
    from oracle.core.models import LeadingIndicator

    indicator = LeadingIndicator("cpu high", "cpu", 90, 5, 0.8, 0.8)
    db.add("indicators", indicator)
    prediction = Prediction("outage", "api", 0.8, "soon", ["cpu high"], [], [])
    db.add("predictions", prediction)
    PredictionFeedback(db).record_outcome(prediction.id, happened=False)
    assert db.list("indicators")[0].confidence < 0.8


def test_accuracy_calculates_precision_recall():
    predictions = [
        Prediction("outage", "api", 0.9, "soon", [], [], [], status="confirmed"),
        Prediction("outage", "api", 0.9, "soon", [], [], [], status="false_positive"),
    ]
    stats = AccuracyCalculator().calculate(predictions, false_negatives=1)
    assert stats.precision == 0.5
    assert stats.recall == 0.5
    assert stats.f1_score == 0.5


def test_accuracy_groups_by_service():
    prediction = Prediction("outage", "api", 0.9, "soon", [], [], [], status="confirmed")
    stats = AccuracyCalculator().calculate([prediction])
    assert stats.by_service["api"]["confirmed"] == 1


def test_feedback_tracks_false_negative(db):
    feedback = PredictionFeedback(db)
    feedback.record_missed_incident()
    assert feedback.accuracy().false_negatives == 1

