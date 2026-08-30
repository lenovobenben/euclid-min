"""确定性、明确非完备的目标相关 beam search。"""

from __future__ import annotations

from .candidates import generate_candidates
from .heuristic import PointDistanceHeuristic
from .index import ExactStateIndex
from .model import SearchGoal, SearchNode, SearchOutcome
from .profiling import SearchTelemetry


class DeterministicBeamSearch:
    """每层只保留评分最优的有限状态；结果不能作为 lower bound。"""

    def search(
        self,
        goal: SearchGoal,
        heuristic: PointDistanceHeuristic,
        *,
        max_score: int,
        beam_width: int,
        max_states: int | None = None,
    ) -> SearchOutcome:
        if max_score < 0:
            raise ValueError("max_score 不能为负数")
        if beam_width < 1:
            raise ValueError("beam_width 至少为 1")
        if max_states is not None and max_states < 1:
            raise ValueError("max_states 至少为 1")

        telemetry = SearchTelemetry()
        initial = SearchNode.initial()
        index = ExactStateIndex()
        with telemetry.measure("state_index_seconds"):
            index.add_if_better(initial.state, 0)
        frontier = [initial]
        expanded_states = 0
        generated_candidates = 0
        accepted_states = 1
        equivalent_pruned = 0
        heuristic_evaluations = 0
        heuristic_pruned = 0
        max_frontier = 1

        with telemetry.measure("goal_test_seconds"):
            initial_reached = goal.reached(initial.state)
        if initial_reached:
            return self._outcome(
                "found",
                initial,
                telemetry,
                expanded_states,
                generated_candidates,
                accepted_states,
                equivalent_pruned,
                max_frontier,
                heuristic_evaluations,
                heuristic_pruned,
            )

        for _depth in range(max_score):
            ranked_children: list[tuple[object, int, SearchNode]] = []
            sequence = 0
            for node in frontier:
                expanded_states += 1
                with telemetry.measure("candidate_generation_seconds"):
                    candidates = generate_candidates(node.state)
                for candidate in candidates:
                    generated_candidates += 1
                    with telemetry.measure("state_expansion_seconds"):
                        child = node.apply(candidate)
                    with telemetry.measure("state_index_seconds"):
                        accepted = index.add_if_better(child.state, child.score)
                    if not accepted:
                        equivalent_pruned += 1
                        continue
                    accepted_states += 1
                    with telemetry.measure("goal_test_seconds"):
                        goal_reached = goal.reached(child.state)
                    if goal_reached:
                        return self._outcome(
                            "found",
                            child,
                            telemetry,
                            expanded_states,
                            generated_candidates,
                            accepted_states,
                            equivalent_pruned,
                            max_frontier,
                            heuristic_evaluations,
                            heuristic_pruned,
                        )
                    with telemetry.measure("heuristic_seconds"):
                        score = heuristic.evaluate(child.state)
                    heuristic_evaluations += 1
                    ranked_children.append((score, sequence, child))
                    sequence += 1
                if max_states is not None and accepted_states >= max_states:
                    return self._outcome(
                        "state_limit",
                        None,
                        telemetry,
                        expanded_states,
                        generated_candidates,
                        accepted_states,
                        equivalent_pruned,
                        max_frontier,
                        heuristic_evaluations,
                        heuristic_pruned,
                    )
            ranked_children.sort(key=lambda item: (item[0], item[1]))
            retained = ranked_children[:beam_width]
            heuristic_pruned += len(ranked_children) - len(retained)
            frontier = [item[2] for item in retained]
            max_frontier = max(max_frontier, len(frontier))
            if not frontier:
                break

        return self._outcome(
            "heuristic_limit",
            None,
            telemetry,
            expanded_states,
            generated_candidates,
            accepted_states,
            equivalent_pruned,
            max_frontier,
            heuristic_evaluations,
            heuristic_pruned,
        )

    @staticmethod
    def _outcome(
        status: str,
        node: SearchNode | None,
        telemetry: SearchTelemetry,
        expanded_states: int,
        generated_candidates: int,
        accepted_states: int,
        equivalent_pruned: int,
        max_frontier: int,
        heuristic_evaluations: int,
        heuristic_pruned: int,
    ) -> SearchOutcome:
        stats = telemetry.snapshot(
            expanded_states=expanded_states,
            generated_candidates=generated_candidates,
            accepted_states=accepted_states,
            equivalent_pruned=equivalent_pruned,
            max_frontier=max_frontier,
            heuristic_evaluations=heuristic_evaluations,
            heuristic_pruned=heuristic_pruned,
        )
        return SearchOutcome(status, node, stats)
