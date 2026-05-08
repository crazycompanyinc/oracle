from __future__ import annotations

from oracle.core.models import PreventionAction, utcnow


class ActionExecutor:
    safe_auto_actions = {"scale_up", "throttle", "notify", "drain"}

    def execute(self, action: PreventionAction) -> PreventionAction:
        if action.action_type not in self.safe_auto_actions and action.auto_executed:
            action.outcome = "skipped"
        else:
            action.outcome = "success"
        action.executed_at = utcnow()
        return action

