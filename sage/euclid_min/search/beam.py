"""确定性、明确非完备的目标相关 beam search。"""

from __future__ import annotations

from collections.abc import Callable

from .candidates import generate_candidates, generate_prefiltered_candidates
from .heuristic import PointDistanceHeuristic, TargetCandidateHeuristic
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
        initial_node: SearchNode | None = None,
        candidate_width: int | None = None,
        candidate_heuristic: TargetCandidateHeuristic | None = None,
        progress: Callable[[dict[str, int | str]], None] | None = None,
    ) -> SearchOutcome:
        if max_score < 0:
            raise ValueError("max_score 不能为负数")
        if beam_width < 1:
            raise ValueError("beam_width 至少为 1")
        if max_states is not None and max_states < 1:
            raise ValueError("max_states 至少为 1")
        if candidate_width is not None and candidate_width < 1:
            raise ValueError("candidate_width 至少为 1")
        if (candidate_width is None) != (candidate_heuristic is None):
            raise ValueError(
                "candidate_width 与 candidate_heuristic 必须同时提供"
            )

        telemetry = SearchTelemetry()
        initial = initial_node or SearchNode.initial()
        if initial.score > max_score:
            raise ValueError("初始节点分数不能超过 max_score")
        index = ExactStateIndex()
        with telemetry.measure("state_index_seconds"):
            index.add_if_better(initial.state, initial.score)
        frontier = [initial]
        expanded_states = 0
        generated_candidates = 0
        accepted_states = 1
        equivalent_pruned = 0
        heuristic_evaluations = 0
        heuristic_pruned = 0
        candidate_prefilter_evaluations = 0
        candidate_prefilter_pruned = 0
        max_frontier = 1

        with telemetry.measure("goal_test_seconds"):
            initial_reached = goal.reached(initial.state)
        if initial_reached:
            return _outcome(
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
                candidate_prefilter_evaluations,
                candidate_prefilter_pruned,
            )

        for depth_offset in range(max_score - initial.score):
            if progress is not None:
                progress(
                    {
                        "event": "layer_start",
                        "score": initial.score + depth_offset,
                        "frontier": len(frontier),
                    }
                )
            ranked_children: list[tuple[object, int, SearchNode]] = []
            sequence = 0
            for node_index, node in enumerate(frontier):
                expanded_states += 1
                raw_operations = 0
                eligible_operations = 0
                if candidate_width is None:
                    with telemetry.measure("candidate_generation_seconds"):
                        candidates = generate_candidates(node.state)
                else:
                    with telemetry.measure("candidate_prefilter_seconds"):
                        candidate_heuristic.prepare_state(node.state)
                        candidates, raw_operations, eligible_operations = (
                            generate_prefiltered_candidates(
                                node.state,
                                limit=candidate_width,
                                score_operation=(
                                    candidate_heuristic.evaluate_points
                                ),
                            )
                        )
                    candidate_prefilter_evaluations += raw_operations
                    candidate_prefilter_pruned += (
                        raw_operations - len(candidates)
                    )
                generated_candidates += len(candidates)
                if progress is not None:
                    progress(
                        {
                            "event": "state_candidates",
                            "score": node.score,
                            "state_index": node_index,
                            "points": len(node.state.points),
                            "max_point_level": max(node.state.point_levels),
                            "candidates": len(candidates),
                            "raw_operations": raw_operations,
                            "eligible_operations": eligible_operations,
                        }
                    )
                for candidate in candidates:
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
                        return _outcome(
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
                            candidate_prefilter_evaluations,
                            candidate_prefilter_pruned,
                        )
                    with telemetry.measure("heuristic_seconds"):
                        score = heuristic.evaluate(child.state)
                    heuristic_evaluations += 1
                    ranked_children.append((score, sequence, child))
                    sequence += 1
                if progress is not None:
                    progress(
                        {
                            "event": "state_end",
                            "score": node.score,
                            "state_index": node_index,
                        }
                    )
                if max_states is not None and accepted_states >= max_states:
                    return _outcome(
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
                        candidate_prefilter_evaluations,
                        candidate_prefilter_pruned,
                    )
            ranked_children.sort(key=lambda item: (item[0], item[1]))
            retained = ranked_children[:beam_width]
            heuristic_pruned += len(ranked_children) - len(retained)
            frontier = [item[2] for item in retained]
            max_frontier = max(max_frontier, len(frontier))
            if progress is not None:
                progress(
                    {
                        "event": "layer_end",
                        "score": initial.score + depth_offset + 1,
                        "frontier": len(frontier),
                        "accepted_states": accepted_states,
                    }
                )
            if not frontier:
                break

        return _outcome(
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
            candidate_prefilter_evaluations,
            candidate_prefilter_pruned,
        )


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
    candidate_prefilter_evaluations: int,
    candidate_prefilter_pruned: int,
) -> SearchOutcome:
    stats = telemetry.snapshot(
        expanded_states=expanded_states,
        generated_candidates=generated_candidates,
        accepted_states=accepted_states,
        equivalent_pruned=equivalent_pruned,
        max_frontier=max_frontier,
        heuristic_evaluations=heuristic_evaluations,
        heuristic_pruned=heuristic_pruned,
        candidate_prefilter_evaluations=candidate_prefilter_evaluations,
        candidate_prefilter_pruned=candidate_prefilter_pruned,
    )
    return SearchOutcome(status, node, stats)
