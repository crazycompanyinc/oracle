from __future__ import annotations

from datetime import timedelta

from oracle.causal.model import CausalModel
from oracle.core.models import MetricPoint, utcnow
from oracle.predictor.indicators import IndicatorMatcher, IndicatorMiner
from oracle.predictor.trends import TrendAnalyzer


def test_indicator_miner_discovers_metrics(incidents):
    indicators = IndicatorMiner().discover(incidents)
    assert any(i.metric_pattern == "redis_connections" for i in indicators)


def test_indicator_matcher_triggers_for_threshold(trained, redis_metrics):
    db, _ = trained
    indicators = db.list("indicators")
    matches = IndicatorMatcher().match(indicators, redis_metrics)
    assert any(match[0].metric_pattern == "redis_connections" for match in matches)


def test_indicator_matcher_ignores_below_threshold(trained):
    db, _ = trained
    point = MetricPoint("payments", "redis_connections", 10)
    assert IndicatorMatcher().match(db.list("indicators"), [point]) == []


def test_trend_analyzer_slope(redis_metrics):
    assert TrendAnalyzer().slope(redis_metrics) > 0


def test_trend_analyzer_eta(redis_metrics):
    eta = TrendAnalyzer().minutes_to_threshold(redis_metrics, 100)
    assert eta is not None
    assert eta > 0


def test_trend_analyzer_score_zero_for_decline():
    now = utcnow()
    points = [
        MetricPoint("api", "cpu", 90, now - timedelta(minutes=10)),
        MetricPoint("api", "cpu", 50, now),
    ]
    assert TrendAnalyzer().score(points, 95) == 0


def test_causal_model_projects_path(incidents):
    model = CausalModel()
    model.train(incidents)
    assert model.project(["redis_connections"], "payment_timeouts") == ["redis_connections", "payment_timeouts"]


def test_causal_model_relatedness(incidents):
    model = CausalModel()
    model.train(incidents)
    assert model.relatedness(["traffic_spike"], "gateway_saturation") > 0


def test_predictor_train_persists_indicators(trained):
    db, _ = trained
    assert len(db.list("indicators")) >= 4


def test_predictor_creates_prediction(trained, redis_metrics):
    db, predictor = trained
    for point in redis_metrics:
        db.add("metrics", point)
    predictions = predictor.predict(service="payments")
    assert predictions
    assert predictions[0].predicted_incident_type == "payment_timeouts"


def test_predictor_confidence_uses_signal_scores(trained, redis_metrics):
    db, predictor = trained
    for point in redis_metrics:
        db.add("metrics", point)
    prediction = predictor.predict(service="payments")[0]
    assert prediction.signal_scores["leading_indicator"] > 0
    assert prediction.confidence >= 0.5


def test_predictor_filters_by_service(trained, redis_metrics):
    db, predictor = trained
    for point in redis_metrics:
        db.add("metrics", point)
    assert predictor.predict(service="gateway") == []

