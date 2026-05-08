from __future__ import annotations

from oracle.core.db import OracleDB
from oracle.core.models import Prediction, PreventionAction, utcnow
from oracle.prevention.actions import ActionExecutor


class PreventionEngine:
    def __init__(
        self,
        db: OracleDB,
        auto_execute_threshold: float = 0.85,
        notify_threshold: float = 0.65,
        monitor_threshold: float = 0.40,
        executor: ActionExecutor | None = None,
    ) -> None:
        self.db = db
        self.auto_execute_threshold = auto_execute_threshold
        self.notify_threshold = notify_threshold
        self.monitor_threshold = monitor_threshold
        self.executor = executor or ActionExecutor()

    def plan(self, prediction: Prediction) -> list[PreventionAction]:
        actions: list[PreventionAction] = []
        for recommendation in prediction.recommended_actions:
            action_type, _, target = recommendation.partition(":")
            actions.append(
                PreventionAction(
                    prediction_id=prediction.id,
                    action_type=action_type or "notify",
                    target=target or prediction.affected_service,
                    confidence_threshold=self.auto_execute_threshold,
                    params={"reason": prediction.predicted_incident_type, "confidence": prediction.confidence},
                )
            )
        if not actions and prediction.confidence >= self.monitor_threshold:
            actions.append(
                PreventionAction(
                    prediction_id=prediction.id,
                    action_type="notify",
                    target=prediction.affected_service,
                    confidence_threshold=self.notify_threshold,
                )
            )
        return actions

    def handle_prediction(self, prediction: Prediction) -> list[PreventionAction]:
        actions = self.plan(prediction)
        for action in actions:
            if prediction.confidence >= self.auto_execute_threshold:
                action.auto_executed = True
                self.executor.execute(action)
                prediction.status = "prevented" if action.outcome == "success" else prediction.status
                prediction.resolved_at = utcnow() if prediction.status == "prevented" else prediction.resolved_at
            elif prediction.confidence >= self.notify_threshold:
                action.outcome = "pending"
            elif prediction.confidence >= self.monitor_threshold:
                action.action_type = "notify"
                action.outcome = "pending"
            else:
                action.outcome = "skipped"
            self.db.add("actions", action)
        self.db.update_prediction(prediction)
        return actions

