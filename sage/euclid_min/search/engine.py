"""有状态上限的确定性均匀成本搜索。"""

from __future__ import annotations

from collections import deque

from .candidates import generate_candidates
from .index import ExactStateIndex
from .model import SearchGoal, SearchNode, SearchOutcome, SearchStats
from .profiling import SearchTelemetry


class BoundedBreadthFirstSearch:
    """按 E-score 分层展开；未触发 state_limit 时对给定深度完备。"""

    def search(
        self,
        goal: SearchGoal,
        *,
        max_score: int,
        max_states: int | None = None,
        initial_frontier: tuple[SearchNode, ...] | None = None,
    ) -> SearchOutcome:
        if max_score < 0:
            raise ValueError("max_score 不能为负数")
        if max_states is not None and max_states < 1:
            raise ValueError("max_states 至少为 1")
        telemetry = SearchTelemetry()

        starting_nodes = initial_frontier or (SearchNode.initial(),)
        if any(node.score > max_score for node in starting_nodes):
            raise ValueError("checkpoint 节点分数超过 max_score")
        index = ExactStateIndex()
        frontier: deque[SearchNode] = deque()
        for node in starting_nodes:
            with telemetry.measure("state_index_seconds"):
                accepted = index.add_if_better(node.state, node.score)
            if accepted:
                frontier.append(node)
        expanded_states = 0
        generated_candidates = 0
        accepted_states = len(frontier)
        equivalent_pruned = 0
        max_frontier = len(frontier)

        for node in frontier:
            with telemetry.measure("goal_test_seconds"):
                goal_reached = goal.reached(node.state)
            if goal_reached:
                return self._outcome(
                    "found",
                    node,
                    expanded_states,
                    generated_candidates,
                    accepted_states,
                    equivalent_pruned,
                    max_frontier,
                    telemetry=telemetry,
                )

        while frontier:
            node = frontier.popleft()
            if node.score >= max_score:
                continue
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
                with telemetry.measure("goal_test_seconds"):
                    goal_reached = goal.reached(child.state)
                if goal_reached:
                    accepted_states += 1
                    return self._outcome(
                        "found",
                        child,
                        expanded_states,
                        generated_candidates,
                        accepted_states,
                        equivalent_pruned,
                        max(max_frontier, len(frontier) + 1),
                        telemetry=telemetry,
                    )
                frontier.append(child)
                accepted_states += 1
                max_frontier = max(max_frontier, len(frontier))

            # 只在一个节点的候选全部展开后暂停，checkpoint 才不会遗漏分支。
            if max_states is not None and accepted_states >= max_states:
                return self._outcome(
                    "state_limit",
                    None,
                    expanded_states,
                    generated_candidates,
                    accepted_states,
                    equivalent_pruned,
                    max_frontier,
                    tuple(frontier),
                    telemetry=telemetry,
                )

        return self._outcome(
            "exhausted",
            None,
            expanded_states,
            generated_candidates,
            accepted_states,
            equivalent_pruned,
            max_frontier,
            telemetry=telemetry,
        )

    @staticmethod
    def _outcome(
        status: str,
        node: SearchNode | None,
        expanded_states: int,
        generated_candidates: int,
        accepted_states: int,
        equivalent_pruned: int,
        max_frontier: int,
        frontier: tuple[SearchNode, ...] = (),
        *,
        telemetry: SearchTelemetry,
    ) -> SearchOutcome:
        return SearchOutcome(
            status,
            node,
            telemetry.snapshot(
                expanded_states=expanded_states,
                generated_candidates=generated_candidates,
                accepted_states=accepted_states,
                equivalent_pruned=equivalent_pruned,
                max_frontier=max_frontier,
            ),
            frontier,
        )
