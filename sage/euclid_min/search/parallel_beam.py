"""进程级并行、带超时保护的非证明 beam search。"""

from __future__ import annotations

from collections.abc import Callable
import multiprocessing
from time import perf_counter

from .candidates import generate_prefiltered_candidates
from .heuristic import PointDistanceHeuristic, TargetCandidateHeuristic
from .model import Candidate, SearchGoal, SearchNode, SearchOutcome
from .profiling import SearchTelemetry


class ParallelHeuristicBeamSearch:
    """并行筛选路径摘要，仅重建每层最终保留的少量精确状态。

    候选预筛、beam 截断、生成层级门和运行时超时都会永久删除分支。因此该类
    只能寻找更短构造，任何未命中结果都不能用于 lower bound 或最优性声明。
    """

    def search(
        self,
        goal: SearchGoal,
        heuristic: PointDistanceHeuristic,
        candidate_heuristic: TargetCandidateHeuristic,
        *,
        max_score: int,
        beam_width: int,
        candidate_width: int,
        workers: int,
        state_timeout_seconds: float,
        diversify_candidates: bool = True,
        initial_node: SearchNode | None = None,
        max_states: int | None = None,
        progress: Callable[[dict[str, int | str]], None] | None = None,
    ) -> SearchOutcome:
        if max_score < 0:
            raise ValueError("max_score 不能为负数")
        if beam_width < 1 or candidate_width < 1:
            raise ValueError("beam_width 和 candidate_width 至少为 1")
        if workers < 2:
            raise ValueError("并行搜索 workers 至少为 2")
        if state_timeout_seconds <= 0:
            raise ValueError("state_timeout_seconds 必须为正数")
        if max_states is not None and max_states < 1:
            raise ValueError("max_states 至少为 1")

        telemetry = SearchTelemetry()
        initial = initial_node or SearchNode.initial()
        if initial.score > max_score:
            raise ValueError("初始节点分数不能超过 max_score")
        frontier = [initial]
        expanded_states = 0
        generated_candidates = 0
        accepted_states = 1
        heuristic_evaluations = 0
        heuristic_pruned = 0
        candidate_prefilter_evaluations = 0
        candidate_prefilter_pruned = 0
        candidate_timeouts = 0
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
                max_frontier,
                heuristic_evaluations,
                heuristic_pruned,
                candidate_prefilter_evaluations,
                candidate_prefilter_pruned,
                candidate_timeouts,
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
            transitions: list[
                tuple[object, int, SearchNode, Candidate]
            ] = []
            sequence = 0
            for node_index, node in enumerate(frontier):
                expanded_states += 1
                with telemetry.measure("candidate_prefilter_seconds"):
                    candidate_heuristic.prepare_state(node.state)
                    candidates, raw_operations, eligible_operations = (
                        generate_prefiltered_candidates(
                            node.state,
                            limit=candidate_width,
                            score_operation=candidate_heuristic.evaluate_points,
                            operation_key=candidate_heuristic.operation_key,
                            operation_level=candidate_heuristic.operation_level,
                            exact_deduplicate=False,
                            diversify=diversify_candidates,
                        )
                    )
                generated_candidates += len(candidates)
                candidate_prefilter_evaluations += raw_operations
                candidate_prefilter_pruned += (
                    raw_operations - len(candidates)
                )
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
                records, timings, timed_out = _score_candidates_parallel(
                    node,
                    candidates,
                    goal,
                    heuristic,
                    workers=workers,
                    timeout_seconds=state_timeout_seconds,
                )
                telemetry.timings["state_expansion_seconds"] += timings[0]
                telemetry.timings["goal_test_seconds"] += timings[1]
                telemetry.timings["heuristic_seconds"] += timings[2]
                candidate_timeouts += timed_out
                accepted_states += len(records)
                for candidate, reached, score in records:
                    if reached:
                        child = node.apply(candidate)
                        return _outcome(
                            "found",
                            child,
                            telemetry,
                            expanded_states,
                            generated_candidates,
                            accepted_states,
                            max_frontier,
                            heuristic_evaluations,
                            heuristic_pruned,
                            candidate_prefilter_evaluations,
                            candidate_prefilter_pruned,
                            candidate_timeouts,
                        )
                    heuristic_evaluations += 1
                    transitions.append((score, sequence, node, candidate))
                    sequence += 1
                if progress is not None:
                    progress(
                        {
                            "event": "state_end",
                            "score": node.score,
                            "state_index": node_index,
                            "timed_out_candidates": timed_out,
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
                        max_frontier,
                        heuristic_evaluations,
                        heuristic_pruned,
                        candidate_prefilter_evaluations,
                        candidate_prefilter_pruned,
                        candidate_timeouts,
                    )

            transitions.sort(key=lambda item: (item[0], item[1]))
            retained = transitions[:beam_width]
            heuristic_pruned += len(transitions) - len(retained)
            frontier = []
            for _score, _sequence, parent, candidate in retained:
                frontier.append(parent.apply(candidate))
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
            max_frontier,
            heuristic_evaluations,
            heuristic_pruned,
            candidate_prefilter_evaluations,
            candidate_prefilter_pruned,
            candidate_timeouts,
        )


def _process_context():
    try:
        return multiprocessing.get_context("fork")
    except ValueError:
        return multiprocessing.get_context("spawn")


def _score_candidates_parallel(
    node: SearchNode,
    candidates: tuple[Candidate, ...],
    goal: SearchGoal,
    heuristic: PointDistanceHeuristic,
    *,
    workers: int,
    timeout_seconds: float,
):
    if not candidates:
        return [], (0.0, 0.0, 0.0), 0
    context = _process_context()
    pool = context.Pool(
        processes=min(workers, len(candidates)),
        initializer=_initialize_worker,
        initargs=(node, goal, heuristic),
    )
    results = [
        pool.apply_async(_score_candidate, ((index, candidate),))
        for index, candidate in enumerate(candidates)
    ]
    deadline = perf_counter() + timeout_seconds
    records = []
    expansion_seconds = 0.0
    goal_seconds = 0.0
    heuristic_seconds = 0.0
    timed_out = 0
    try:
        for result in results:
            try:
                record = result.get(
                    timeout=max(0.0, deadline - perf_counter())
                )
            except multiprocessing.TimeoutError:
                timed_out += 1
                continue
            (
                candidate_index,
                candidate,
                reached,
                score,
                elapsed_expansion,
                elapsed_goal,
                elapsed_heuristic,
            ) = record
            records.append((candidate_index, candidate, reached, score))
            expansion_seconds += elapsed_expansion
            goal_seconds += elapsed_goal
            heuristic_seconds += elapsed_heuristic
    except BaseException:
        pool.terminate()
        pool.join()
        raise
    if timed_out:
        pool.terminate()
    else:
        pool.close()
    pool.join()
    records.sort(key=lambda item: item[0])
    compact = [
        (candidate, reached, score)
        for _index, candidate, reached, score in records
    ]
    return (
        compact,
        (expansion_seconds, goal_seconds, heuristic_seconds),
        timed_out,
    )


_WORKER_NODE: SearchNode | None = None
_WORKER_GOAL: SearchGoal | None = None
_WORKER_HEURISTIC: PointDistanceHeuristic | None = None


def _initialize_worker(
    node: SearchNode,
    goal: SearchGoal,
    heuristic: PointDistanceHeuristic,
) -> None:
    global _WORKER_NODE, _WORKER_GOAL, _WORKER_HEURISTIC
    _WORKER_NODE = node
    _WORKER_GOAL = goal
    _WORKER_HEURISTIC = heuristic


def _score_candidate(indexed_candidate: tuple[int, Candidate]):
    if (
        _WORKER_NODE is None
        or _WORKER_GOAL is None
        or _WORKER_HEURISTIC is None
    ):
        raise RuntimeError("并行候选 worker 尚未初始化")
    candidate_index, candidate = indexed_candidate
    started_at = perf_counter()
    child = _WORKER_NODE.apply(candidate)
    expansion_seconds = perf_counter() - started_at
    started_at = perf_counter()
    reached = _WORKER_GOAL.reached(child.state)
    goal_seconds = perf_counter() - started_at
    heuristic_seconds = 0.0
    score = None
    if not reached:
        started_at = perf_counter()
        score = _WORKER_HEURISTIC.evaluate(child.state)
        heuristic_seconds = perf_counter() - started_at
    return (
        candidate_index,
        candidate,
        reached,
        score,
        expansion_seconds,
        goal_seconds,
        heuristic_seconds,
    )


def _outcome(
    status: str,
    node: SearchNode | None,
    telemetry: SearchTelemetry,
    expanded_states: int,
    generated_candidates: int,
    accepted_states: int,
    max_frontier: int,
    heuristic_evaluations: int,
    heuristic_pruned: int,
    candidate_prefilter_evaluations: int,
    candidate_prefilter_pruned: int,
    candidate_timeouts: int,
) -> SearchOutcome:
    stats = telemetry.snapshot(
        expanded_states=expanded_states,
        generated_candidates=generated_candidates,
        accepted_states=accepted_states,
        equivalent_pruned=0,
        max_frontier=max_frontier,
        heuristic_evaluations=heuristic_evaluations,
        heuristic_pruned=heuristic_pruned,
        candidate_prefilter_evaluations=candidate_prefilter_evaluations,
        candidate_prefilter_pruned=candidate_prefilter_pruned,
        candidate_timeouts=candidate_timeouts,
    )
    return SearchOutcome(status, node, stats)
