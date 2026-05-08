from __future__ import annotations

from collections import Counter, defaultdict

from oracle.causal.model import CausalModel
from oracle.core.db import OracleDB
from oracle.core.models import Incident, LeadingIndicator, MetricPoint, Prediction
from oracle.predictor.indicators import IndicatorMatcher, IndicatorMiner
from oracle.predictor.trends import TrendAnalyzer


class IncidentPredictor:
    weights = {
        "leading_indicator": 0.32,
        "causal_chain": 0.22,
        "pattern_match": 0.18,
        "trend": 0.14,
        "correlation": 0.08,
        "deployment_risk": 0.06,
    }

    def __init__(self, db: OracleDB, causal_model: CausalModel | None = None) -> None:
        self.db = db
        self.causal_model = causal_model or CausalModel()
        self.matcher = IndicatorMatcher()
        self.miner = IndicatorMiner()
        self.trends = TrendAnalyzer()

    def train(self, incidents: list[Incident]) -> list[LeadingIndicator]:
        self.db.replace("incidents", incidents)
        self.causal_model.train(incidents)
        indicators = self.miner.discover(incidents)
        self.db.replace("indicators", indicators)
        return indicators

    def predict(self, service: str | None = None) -> list[Prediction]:
        metrics: list[MetricPoint] = self.db.list("metrics")
        indicators: list[LeadingIndicator] = self.db.list("indicators")
        incidents: list[Incident] = self.db.list("incidents")
        if service:
            metrics = [m for m in metrics if m.service == service]
            indicators = [i for i in indicators if i.affected_service in {service, "*"}]
        matches = self.matcher.match(indicators, metrics)
        grouped: dict[tuple[str, str], list[tuple[LeadingIndicator, float]]] = defaultdict(list)
        for indicator, score in matches:
            grouped[(indicator.affected_service, indicator.incident_type)].append((indicator, score))
        predictions = [self._prediction_for(group, metrics, incidents) for group in grouped.values()]
        for prediction in predictions:
            self.db.add("predictions", prediction)
        return predictions

    def _prediction_for(
        self,
        matches: list[tuple[LeadingIndicator, float]],
        metrics: list[MetricPoint],
        incidents: list[Incident],
    ) -> Prediction:
        indicator_scores = [score for _, score in matches]
        indicator_score = max(indicator_scores)
        indicator = matches[0][0]
        active = [m.metric_pattern for m, _ in matches]
        target = indicator.incident_type
        causal_path = self.causal_model.project(active, target=target) or active + [target]
        causal_score = self.causal_model.relatedness(active, target)
        pattern_score = self._pattern_score(active, incidents, target)
        trend_score = self._trend_score(indicator, metrics)
        correlation_score = self._correlation_score(active, incidents, target)
        deployment_score = self._deployment_risk(metrics, incidents, indicator.affected_service)
        signal_scores = {
            "leading_indicator": indicator_score,
            "causal_chain": causal_score,
            "pattern_match": pattern_score,
            "trend": trend_score,
            "correlation": correlation_score,
            "deployment_risk": deployment_score,
        }
        confidence = sum(signal_scores[name] * self.weights[name] for name in self.weights)
        confidence = min(0.99, max(confidence, indicator_score * 0.9))
        return Prediction(
            predicted_incident_type=target,
            affected_service=indicator.affected_service,
            confidence=round(confidence, 3),
            time_horizon=f"in {indicator.expected_horizon_minutes} minutes",
            leading_indicators=[m.name for m, _ in matches],
            causal_chain=causal_path,
            recommended_actions=self._recommend(target, indicator.affected_service),
            signal_scores={k: round(v, 3) for k, v in signal_scores.items()},
        )

    def _pattern_score(self, active: list[str], incidents: list[Incident], target: str) -> float:
        relevant = [i for i in incidents if i.incident_type == target]
        if not relevant:
            return 0.0
        hits = sum(1 for incident in relevant if set(active) & set(incident.signals + list(incident.metrics)))
        return hits / len(relevant)

    def _trend_score(self, indicator: LeadingIndicator, metrics: list[MetricPoint]) -> float:
        points = [p for p in metrics if p.service == indicator.affected_service and p.name == indicator.metric_pattern]
        return self.trends.score(points, indicator.threshold, horizon_minutes=60)

    def _correlation_score(self, active: list[str], incidents: list[Incident], target: str) -> float:
        co_occurrences = Counter()
        totals = Counter()
        for incident in incidents:
            signals = set(incident.signals + list(incident.metrics))
            for signal in active:
                if signal in signals:
                    totals[signal] += 1
                    if incident.incident_type == target:
                        co_occurrences[signal] += 1
        ratios = [co_occurrences[s] / totals[s] for s in active if totals[s]]
        return max(ratios) if ratios else 0.0

    def _deployment_risk(self, metrics: list[MetricPoint], incidents: list[Incident], service: str) -> float:
        deploy_metrics = [m for m in metrics if m.service == service and m.name.startswith("deploy_")]
        if not deploy_metrics:
            return 0.0
        risk_factors = {m.name for m in deploy_metrics if m.value > 0}
        past = [i for i in incidents if i.service == service and any(s.startswith("deploy_") for s in i.signals)]
        if not past:
            return 0.4 if risk_factors else 0.0
        past_factors = set().union(*(set(i.signals) for i in past))
        overlap = len(risk_factors & past_factors)
        return min(1.0, overlap / max(1, len(risk_factors)))

    def _recommend(self, incident_type: str, service: str) -> list[str]:
        if "redis" in incident_type or "timeout" in incident_type:
            return [f"scale_up:{service}", f"notify:{service}"]
        if "migration" in incident_type or "rollback" in incident_type:
            return [f"rollback:{service}", f"notify:{service}"]
        if "traffic" in incident_type or "saturation" in incident_type:
            return [f"throttle:{service}", f"scale_up:{service}"]
        return [f"notify:{service}", f"restart:{service}"]

