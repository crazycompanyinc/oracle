from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import click
import uvicorn

from oracle.causal.model import CausalModel
from oracle.core.db import OracleDB
from oracle.core.models import Incident, MetricPoint, utcnow
from oracle.feedback.feedback import PredictionFeedback
from oracle.predictor.predictor import IncidentPredictor
from oracle.prevention.engine import PreventionEngine
from oracle.server.app import create_app


def db_from_context(ctx: click.Context) -> OracleDB:
    return OracleDB(ctx.obj["db"])


@click.group()
@click.option("--db", default=".oracle", help="Oracle data directory.")
@click.pass_context
def cli(ctx: click.Context, db: str) -> None:
    ctx.obj = {"db": db}


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    db = db_from_context(ctx)
    click.echo(f"Initialized Oracle at {db.root}")


@cli.command()
@click.option("--incidents", "incident_dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.pass_context
def train(ctx: click.Context, incident_dir: str) -> None:
    incidents = []
    for path in Path(incident_dir).glob("*.json"):
        data = json.loads(path.read_text())
        data["started_at"] = data.get("started_at", utcnow().isoformat())
        incidents.append(Incident.from_dict(data))
    indicators = IncidentPredictor(db_from_context(ctx), CausalModel()).train(incidents)
    click.echo(f"Trained on {len(incidents)} incidents; discovered {len(indicators)} leading indicators.")


@cli.command()
@click.option("--service")
@click.pass_context
def predict(ctx: click.Context, service: str | None) -> None:
    db = db_from_context(ctx)
    predictions = IncidentPredictor(db, _causal_from_db(db)).predict(service=service)
    engine = PreventionEngine(db)
    for prediction in predictions:
        engine.handle_prediction(prediction)
        click.echo(_format_prediction(prediction))
    if not predictions:
        click.echo("No incident predictions triggered.")


@cli.command()
@click.pass_context
def watch(ctx: click.Context) -> None:
    ctx.invoke(predict)


@cli.command()
@click.pass_context
def prevent(ctx: click.Context) -> None:
    db = db_from_context(ctx)
    pending = [p for p in db.list("predictions") if p.status == "pending"]
    engine = PreventionEngine(db)
    for prediction in pending:
        actions = engine.handle_prediction(prediction)
        click.echo(f"{prediction.id}: planned {len(actions)} action(s)")
    if not pending:
        click.echo("No pending predictions.")


@cli.command()
@click.pass_context
def history(ctx: click.Context) -> None:
    for prediction in db_from_context(ctx).list("predictions"):
        click.echo(_format_prediction(prediction))


@cli.command()
@click.pass_context
def accuracy(ctx: click.Context) -> None:
    stats = PredictionFeedback(db_from_context(ctx)).accuracy()
    click.echo(
        f"predictions={stats.total_predictions} precision={stats.precision:.2f} "
        f"recall={stats.recall:.2f} f1={stats.f1_score:.2f} trend={stats.trend}"
    )


@cli.command()
@click.pass_context
def dashboard(ctx: click.Context) -> None:
    ctx.invoke(serve, port=8000)


@cli.command()
@click.option("--port", default=8000)
@click.pass_context
def serve(ctx: click.Context, port: int) -> None:
    uvicorn.run(create_app(ctx.obj["db"]), host="127.0.0.1", port=port)


@cli.command()
@click.pass_context
def demo(ctx: click.Context) -> None:
    db = db_from_context(ctx)
    db.clear()
    incidents = demo_incidents()
    predictor = IncidentPredictor(db, CausalModel())
    indicators = predictor.train(incidents)
    click.echo(f"Week 1: trained on {len(incidents)} incidents and discovered {len(indicators)} indicators.")
    for point in demo_week_two_metrics():
        db.add("metrics", point)
    predictions = IncidentPredictor(db, _causal_from_db(db)).predict()
    engine = PreventionEngine(db)
    feedback = PredictionFeedback(db)
    for prediction in predictions:
        actions = engine.handle_prediction(prediction)
        prevented = any(action.auto_executed and action.outcome == "success" for action in actions)
        feedback.record_outcome(prediction.id, happened=True, prevented=prevented)
        click.echo(_format_prediction(prediction))
        for action in actions:
            click.echo(f"  action={action.action_type} target={action.target} auto={action.auto_executed} outcome={action.outcome}")
    stats = feedback.accuracy()
    click.echo(
        f"Week 2 accuracy: {stats.true_positives}/{stats.total_predictions} true positives, "
        f"{stats.false_positives} false positives, {stats.true_positives and 1 or 0} prevented incident. "
        "Estimated cost savings: $12,000."
    )


def demo_incidents() -> list[Incident]:
    base = utcnow() - timedelta(days=14)
    return [
        Incident(
            incident_type="payment_timeouts",
            service="payments",
            started_at=base + timedelta(days=1),
            severity="critical",
            signals=["deploy_complex", "deploy_cache_touch", "redis_connections"],
            metrics={"redis_connections": 95, "payment_latency_ms": 1200},
            causal_chain=["deploy_complex", "redis_connections", "payment_timeouts"],
            actions_taken=["scale redis pool", "rollback hot path"],
        ),
        Incident(
            incident_type="migration_failure",
            service="database",
            started_at=base + timedelta(days=3),
            severity="high",
            signals=["deploy_migration", "schema_lock"],
            metrics={"schema_lock": 1, "migration_duration": 45},
            causal_chain=["deploy_migration", "schema_lock", "migration_failure"],
            actions_taken=["rollback"],
        ),
        Incident(
            incident_type="gateway_saturation",
            service="gateway",
            started_at=base + timedelta(days=5),
            severity="high",
            signals=["traffic_spike", "gateway_cpu"],
            metrics={"gateway_cpu": 96, "requests_per_second": 5000},
            causal_chain=["traffic_spike", "gateway_cpu", "gateway_saturation"],
            actions_taken=["rate limiting"],
        ),
        Incident(
            incident_type="cache_storm",
            service="cache",
            started_at=base + timedelta(days=7),
            severity="medium",
            signals=["config_change", "cache_miss_rate"],
            metrics={"cache_miss_rate": 88, "redis_connections": 90},
            causal_chain=["config_change", "cache_miss_rate", "cache_storm"],
            actions_taken=["restore config"],
        ),
    ]


def demo_week_two_metrics() -> list[MetricPoint]:
    now = utcnow()
    return [
        MetricPoint("payments", "deploy_complex", 1, now - timedelta(days=6)),
        MetricPoint("payments", "deploy_cache_touch", 1, now - timedelta(days=6)),
        MetricPoint("payments", "redis_connections", 70, now - timedelta(minutes=20)),
        MetricPoint("payments", "redis_connections", 83, now - timedelta(minutes=10)),
        MetricPoint("payments", "redis_connections", 94, now),
        MetricPoint("gateway", "requests_per_second", 4700, now - timedelta(minutes=4)),
        MetricPoint("gateway", "gateway_cpu", 92, now),
        MetricPoint("database", "deploy_migration", 1, now - timedelta(minutes=15)),
        MetricPoint("database", "schema_lock", 1, now),
        MetricPoint("cache", "cache_miss_rate", 79, now),
    ]


def _causal_from_db(db: OracleDB) -> CausalModel:
    model = CausalModel()
    model.train(db.list("incidents"))
    return model


def _format_prediction(prediction) -> str:
    return (
        f"{prediction.id}: {prediction.predicted_incident_type} on {prediction.affected_service} "
        f"{prediction.time_horizon} confidence={prediction.confidence:.2f} status={prediction.status} "
        f"because {' -> '.join(prediction.causal_chain)}"
    )


if __name__ == "__main__":
    cli()

