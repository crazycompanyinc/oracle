from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {k: _encode(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    return value


def _parse_dt(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


class Serializable:
    def to_dict(self) -> dict[str, Any]:
        return _encode(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        values = {}
        for item in fields(cls):
            if item.name not in data:
                continue
            value = data[item.name]
            if item.name in {"timestamp", "started_at", "resolved_at", "executed_at", "created_at", "discovered_at"}:
                value = _parse_dt(value)
            values[item.name] = value
        return cls(**values)


@dataclass
class MetricPoint(Serializable):
    service: str
    name: str
    value: float
    timestamp: datetime = field(default_factory=utcnow)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Incident(Serializable):
    incident_type: str
    service: str
    started_at: datetime
    resolved_at: datetime | None = None
    severity: str = "medium"
    signals: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    causal_chain: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("inc"))


@dataclass
class LeadingIndicator(Serializable):
    name: str
    metric_pattern: str
    threshold: float
    time_window: int
    confidence: float
    historical_accuracy: float
    false_positive_rate: float = 0.0
    discovered_at: datetime = field(default_factory=utcnow)
    id: str = field(default_factory=lambda: new_id("ind"))
    incident_type: str = "unknown"
    affected_service: str = "*"
    direction: Literal["above", "below"] = "above"
    expected_horizon_minutes: int = 45


@dataclass
class Prediction(Serializable):
    predicted_incident_type: str
    affected_service: str
    confidence: float
    time_horizon: str
    leading_indicators: list[str]
    causal_chain: list[str]
    recommended_actions: list[str]
    status: Literal["pending", "confirmed", "prevented", "false_positive", "expired"] = "pending"
    created_at: datetime = field(default_factory=utcnow)
    resolved_at: datetime | None = None
    id: str = field(default_factory=lambda: new_id("pred"))
    signal_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class PreventionAction(Serializable):
    prediction_id: str
    action_type: Literal["scale_up", "rollback", "restart", "drain", "throttle", "notify", "custom"]
    target: str
    params: dict[str, Any] = field(default_factory=dict)
    auto_executed: bool = False
    outcome: Literal["pending", "success", "failed", "skipped"] = "pending"
    confidence_threshold: float = 0.85
    executed_at: datetime | None = None
    id: str = field(default_factory=lambda: new_id("act"))


@dataclass
class PredictionAccuracy(Serializable):
    total_predictions: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    by_service: dict[str, dict[str, int]] = field(default_factory=dict)
    by_incident_type: dict[str, dict[str, int]] = field(default_factory=dict)
    by_time_period: dict[str, dict[str, int]] = field(default_factory=dict)
    trend: str = "stable"
