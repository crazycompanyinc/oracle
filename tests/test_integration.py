from __future__ import annotations

from click.testing import CliRunner

from oracle.cli import cli, demo_week_two_metrics
from oracle.dashboard.api import DashboardAPI
from oracle.feedback.feedback import PredictionFeedback
from oracle.predictor.predictor import IncidentPredictor
from oracle.prevention.engine import PreventionEngine
from oracle.server.app import create_app
from oracle.telemetry.collector import MetricsCollector
from oracle.telemetry.sources import InMemoryMetricSource


def test_collector_ingests_source(db, redis_metrics):
    collector = MetricsCollector(db, [InMemoryMetricSource(redis_metrics)])
    assert len(collector.collect()) == 3
    assert len(db.list("metrics")) == 3


def test_full_prediction_prevention_feedback_cycle(trained):
    db, predictor = trained
    for point in demo_week_two_metrics():
        db.add("metrics", point)
    predictions = predictor.predict()
    assert len(predictions) >= 4
    engine = PreventionEngine(db)
    feedback = PredictionFeedback(db)
    for prediction in predictions:
        actions = engine.handle_prediction(prediction)
        feedback.record_outcome(prediction.id, happened=True, prevented=any(a.auto_executed for a in actions))
    stats = feedback.accuracy()
    assert stats.true_positives == len(predictions)
    assert stats.false_positives == 0


def test_dashboard_snapshot_contains_core_sections(trained, redis_metrics):
    db, predictor = trained
    for point in redis_metrics:
        db.add("metrics", point)
    predictor.predict()
    snapshot = DashboardAPI(db).snapshot()
    assert {"predictions", "actions", "accuracy", "indicators"} <= set(snapshot)


def test_fastapi_app_health_route():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/predict" in paths


def test_cli_init(tmp_path):
    result = CliRunner().invoke(cli, ["--db", str(tmp_path / "db"), "init"])
    assert result.exit_code == 0
    assert "Initialized Oracle" in result.output


def test_cli_demo_runs(tmp_path):
    result = CliRunner().invoke(cli, ["--db", str(tmp_path / "db"), "demo"])
    assert result.exit_code == 0
    assert "Week 1" in result.output
    assert "Week 2 accuracy" in result.output

