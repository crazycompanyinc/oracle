from __future__ import annotations

from oracle.core.models import Prediction, PreventionAction
from oracle.prevention.actions import ActionExecutor
from oracle.prevention.engine import PreventionEngine


def test_prevention_plan_from_recommendations(db):
    prediction = Prediction("payment_timeouts", "payments", 0.7, "soon", [], [], ["scale_up:payments"])
    actions = PreventionEngine(db).plan(prediction)
    assert actions[0].action_type == "scale_up"


def test_prevention_auto_executes_high_confidence(db):
    prediction = Prediction("payment_timeouts", "payments", 0.9, "soon", [], [], ["scale_up:payments"])
    db.add("predictions", prediction)
    actions = PreventionEngine(db).handle_prediction(prediction)
    assert actions[0].auto_executed is True
    assert actions[0].outcome == "success"


def test_prevention_marks_prediction_prevented(db):
    prediction = Prediction("payment_timeouts", "payments", 0.9, "soon", [], [], ["scale_up:payments"])
    db.add("predictions", prediction)
    PreventionEngine(db).handle_prediction(prediction)
    assert db.list("predictions")[0].status == "prevented"


def test_prevention_notifies_medium_confidence(db):
    prediction = Prediction("gateway_saturation", "gateway", 0.7, "soon", [], [], ["throttle:gateway"])
    db.add("predictions", prediction)
    action = PreventionEngine(db).handle_prediction(prediction)[0]
    assert action.outcome == "pending"
    assert action.auto_executed is False


def test_prevention_skips_low_confidence(db):
    prediction = Prediction("cache_storm", "cache", 0.2, "soon", [], [], ["notify:cache"])
    db.add("predictions", prediction)
    action = PreventionEngine(db).handle_prediction(prediction)[0]
    assert action.outcome == "skipped"


def test_executor_skips_unsafe_auto_action():
    action = PreventionAction("pred", "rollback", "api", auto_executed=True)
    assert ActionExecutor().execute(action).outcome == "skipped"


def test_executor_allows_safe_action():
    action = PreventionAction("pred", "throttle", "gateway", auto_executed=True)
    assert ActionExecutor().execute(action).outcome == "success"

