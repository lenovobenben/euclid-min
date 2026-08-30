"""不参与数学结论的搜索阶段计时。"""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter

from .model import SearchStats


class SearchTelemetry:
    """汇总阶段耗时；计时不会改变候选或状态判断。"""

    def __init__(self) -> None:
        self.started_at = perf_counter()
        self.timings = {
            "candidate_generation_seconds": 0.0,
            "state_expansion_seconds": 0.0,
            "state_index_seconds": 0.0,
            "goal_test_seconds": 0.0,
            "heuristic_seconds": 0.0,
        }

    @contextmanager
    def measure(self, name: str):
        started_at = perf_counter()
        try:
            yield
        finally:
            self.timings[name] += perf_counter() - started_at

    def snapshot(
        self,
        *,
        expanded_states: int,
        generated_candidates: int,
        accepted_states: int,
        equivalent_pruned: int,
        max_frontier: int,
        heuristic_evaluations: int = 0,
        heuristic_pruned: int = 0,
    ) -> SearchStats:
        return SearchStats(
            expanded_states=expanded_states,
            generated_candidates=generated_candidates,
            accepted_states=accepted_states,
            equivalent_pruned=equivalent_pruned,
            max_frontier=max_frontier,
            heuristic_evaluations=heuristic_evaluations,
            heuristic_pruned=heuristic_pruned,
            elapsed_seconds=perf_counter() - self.started_at,
            **self.timings,
        )
