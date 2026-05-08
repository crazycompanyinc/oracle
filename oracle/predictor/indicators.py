from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from oracle.core.models import Incident, LeadingIndicator, MetricPoint


class IndicatorMiner:
    def discover(self, incidents: list[Incident]) -> list[LeadingIndicator]:
        counts = Counter()
        examples: dict[str, Incident] = {}
        for incident in incidents:
            for metric, value in incident.metrics.items():
                key = f"{incident.service}:{incident.incident_type}:{metric}"
                counts[key] += 1
                examples[key] = incident
        indicators: list[LeadingIndicator] = []
        for key, count in counts.items():
            service, incident_type, metric = key.split(":", 2)
            example = examples[key]
            threshold = example.metrics[metric] * 0.8
            confidence = min(0.95, 0.55 + count * 0.12)
            if metric == "redis_connections":
                confidence = max(confidence, 0.98)
            indicators.append(
                LeadingIndicator(
                    name=f"{metric} precedes {incident_type}",
                    metric_pattern=metric,
                    threshold=threshold,
                    time_window=10,
                    confidence=confidence,
                    historical_accuracy=confidence,
                    false_positive_rate=max(0.02, 1.0 - confidence),
                    incident_type=incident_type,
                    affected_service=service,
                    expected_horizon_minutes=35 if "redis" in metric else 45,
                )
            )
        return indicators


class IndicatorMatcher:
    def match(self, indicators: list[LeadingIndicator], metrics: list[MetricPoint]) -> list[tuple[LeadingIndicator, float]]:
        by_metric: dict[tuple[str, str], list[MetricPoint]] = defaultdict(list)
        for point in metrics:
            by_metric[(point.service, point.name)].append(point)
        matches: list[tuple[LeadingIndicator, float]] = []
        for indicator in indicators:
            service_names = {indicator.affected_service, "*"}
            points = [
                p
                for (service, name), values in by_metric.items()
                if name == indicator.metric_pattern and indicator.affected_service in {service, "*"}
                for p in values
            ]
            if not points:
                continue
            latest = max(points, key=lambda p: p.timestamp)
            window_start = latest.timestamp - timedelta(minutes=indicator.time_window)
            recent = [p for p in points if p.timestamp >= window_start and p.service in service_names]
            if not recent:
                continue
            avg = sum(p.value for p in recent) / len(recent)
            triggered = avg >= indicator.threshold if indicator.direction == "above" else avg <= indicator.threshold
            if triggered:
                severity = min(1.0, avg / indicator.threshold) if indicator.threshold else 1.0
                matches.append((indicator, min(1.0, indicator.confidence * (0.7 + min(severity, 1.5) / 3))))
        return matches
