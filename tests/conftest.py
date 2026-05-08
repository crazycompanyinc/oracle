from __future__ import annotations

from datetime import timedelta

import pytest

from oracle.causal.model import CausalModel
from oracle.cli import demo_incidents
from oracle.core.db import OracleDB
from oracle.core.models import Incident, MetricPoint, utcnow
from oracle.predictor.predictor import IncidentPredictor


@pytest.fixture
def db(tmp_path):
    return OracleDB(tmp_path / "oracle-db")


@pytest.fixture
def incidents():
    return demo_incidents()


@pytest.fixture
def trained(db, incidents):
    model = CausalModel()
    predictor = IncidentPredictor(db, model)
    predictor.train(incidents)
    return db, predictor


@pytest.fixture
def redis_metrics():
    now = utcnow()
    return [
        MetricPoint("payments", "redis_connections", 65, now - timedelta(minutes=20)),
        MetricPoint("payments", "redis_connections", 82, now - timedelta(minutes=10)),
        MetricPoint("payments", "redis_connections", 94, now),
    ]


@pytest.fixture
def sample_incident():
    return Incident(
        incident_type="payment_timeouts",
        service="payments",
        started_at=utcnow(),
        signals=["redis_connections"],
        metrics={"redis_connections": 95},
        causal_chain=["redis_connections", "payment_timeouts"],
    )

