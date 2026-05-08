from __future__ import annotations

from collections import defaultdict, deque

from oracle.core.models import Incident


class CausalModel:
    """CausalChain-style directed graph with weighted transitions."""

    def __init__(self) -> None:
        self.edges: dict[str, dict[str, float]] = defaultdict(dict)

    def observe_chain(self, chain: list[str], weight: float = 1.0) -> None:
        for left, right in zip(chain, chain[1:]):
            self.edges[left][right] = self.edges[left].get(right, 0.0) + weight

    def train(self, incidents: list[Incident]) -> None:
        for incident in incidents:
            if incident.causal_chain:
                self.observe_chain(incident.causal_chain)

    def project(self, active_causes: list[str], target: str | None = None, max_depth: int = 4) -> list[str]:
        queue = deque((cause, [cause], 1.0) for cause in active_causes)
        best_path: list[str] = []
        best_score = 0.0
        while queue:
            node, path, score = queue.popleft()
            if target and node == target and score > best_score:
                best_path, best_score = path, score
            if not target and score > best_score:
                best_path, best_score = path, score
            if len(path) >= max_depth:
                continue
            total = sum(self.edges.get(node, {}).values()) or 1.0
            for nxt, weight in self.edges.get(node, {}).items():
                if nxt not in path:
                    queue.append((nxt, path + [nxt], score * (weight / total)))
        return best_path

    def relatedness(self, active_causes: list[str], target: str) -> float:
        path = self.project(active_causes, target=target)
        return min(1.0, len(path) / 4) if path else 0.0

