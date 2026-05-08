from __future__ import annotations

from oracle.core.models import Incident, LeadingIndicator, MetricPoint, Prediction, PreventionAction, utcnow


def test_db_initializes_collections(db):
    assert db.list("incidents") == []
    assert db.list("indicators") == []
    assert db.list("metrics") == []


def test_db_add_and_list_incident(db, sample_incident):
    db.add("incidents", sample_incident)
    loaded = db.list("incidents")
    assert loaded[0].incident_type == "payment_timeouts"
    assert loaded[0].started_at == sample_incident.started_at


def test_db_replace_collection(db, sample_incident):
    db.add("incidents", sample_incident)
    db.replace("incidents", [])
    assert db.list("incidents") == []


def test_db_update_prediction(db):
    prediction = Prediction("outage", "api", 0.7, "in 1 hour", [], [], [])
    db.add("predictions", prediction)
    prediction.status = "confirmed"
    db.update_prediction(prediction)
    assert db.list("predictions")[0].status == "confirmed"


def test_model_roundtrip_datetime():
    point = MetricPoint("api", "cpu", 90, utcnow())
    loaded = MetricPoint.from_dict(point.to_dict())
    assert loaded.timestamp == point.timestamp


def test_leading_indicator_defaults():
    indicator = LeadingIndicator("cpu high", "cpu", 90, 5, 0.8, 0.75)
    assert indicator.direction == "above"
    assert indicator.expected_horizon_minutes == 45


def test_prevention_action_defaults():
    action = PreventionAction("pred_1", "notify", "api")
    assert action.outcome == "pending"
    assert action.auto_executed is False

