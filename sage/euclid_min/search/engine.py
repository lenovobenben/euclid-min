"""有状态上限的确定性均匀成本搜索。"""

from __future__ import annotations

from collections import deque

from .candidates import generate_candidates
from .index import ExactStateIndex
from .model import SearchGoal, SearchNode, SearchOutcome, SearchStats


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

        starting_nodes = initial_frontier or (SearchNode.initial(),)
        if any(node.score > max_score for node in starting_nodes):
            raise ValueError("checkpoint 节点分数超过 max_score")
        index = ExactStateIndex()
        frontier: deque[SearchNode] = deque()
        for node in starting_nodes:
            if index.add_if_better(node.state, node.score):
                frontier.append(node)
        expanded_states = 0
        generated_candidates = 0
        accepted_states = len(frontier)
        equivalent_pruned = 0
        max_frontier = len(frontier)

        for node in frontier:
            if goal.reached(node.state):
                return self._outcome(
                    "found",
                    node,
                    expanded_states,
                    generated_candidates,
                    accepted_states,
                    equivalent_pruned,
                    max_frontier,
                )

        while frontier:
            node = frontier.popleft()
            if node.score >= max_score:
                continue
            expanded_states += 1
            for candidate in generate_candidates(node.state):
                generated_candidates += 1
                child = node.apply(candidate)
                if not index.add_if_better(child.state, child.score):
                    equivalent_pruned += 1
                    continue
                if goal.reached(child.state):
                    accepted_states += 1
                    return self._outcome(
                        "found",
                        child,
                        expanded_states,
                        generated_candidates,
                        accepted_states,
                        equivalent_pruned,
                        max(max_frontier, len(frontier) + 1),
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
                )

        return self._outcome(
            "exhausted",
            None,
            expanded_states,
            generated_candidates,
            accepted_states,
            equivalent_pruned,
            max_frontier,
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
    ) -> SearchOutcome:
        return SearchOutcome(
            status,
            node,
            SearchStats(
                expanded_states=expanded_states,
                generated_candidates=generated_candidates,
                accepted_states=accepted_states,
                equivalent_pruned=equivalent_pruned,
                max_frontier=max_frontier,
            ),
            frontier,
        )
