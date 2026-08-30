"""搜索候选、节点、目标和结果数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..geometry import Circle, Drawable, Line, Point
from ..state import GeometryState
from ..target import reached_targets


@dataclass(frozen=True, slots=True)
class SearchStep:
    """一项尚未分配证书 ID 的基础绘制操作。"""

    op: str
    first: Point
    second: Point

    def drawable(self) -> Drawable:
        if self.op == "line":
            return Line.through(self.first, self.second)
        if self.op == "circle":
            return Circle.through(self.first, self.second)
        raise ValueError(f"不支持的搜索操作 {self.op!r}")


@dataclass(frozen=True, slots=True)
class Candidate(SearchStep):
    """当前状态中一个不同的新直线或圆候选。"""


@dataclass(slots=True)
class SearchNode:
    """一个完整数学状态及其最低成本确定性路径。"""

    state: GeometryState
    steps: tuple[SearchStep, ...] = ()

    @classmethod
    def initial(cls) -> "SearchNode":
        return cls(GeometryState.fixed_initial())

    @property
    def score(self) -> int:
        return len(self.steps)

    def apply(self, candidate: Candidate) -> "SearchNode":
        child_state = self.state.clone()
        if candidate.op == "line":
            addition = child_state.draw_line(candidate.first, candidate.second)
        elif candidate.op == "circle":
            addition = child_state.draw_circle(candidate.first, candidate.second)
        else:
            raise ValueError(f"不支持的搜索操作 {candidate.op!r}")
        if not addition.new_object:
            raise ValueError("搜索候选必须产生一个不同的新对象")
        step = SearchStep(candidate.op, candidate.first, candidate.second)
        return SearchNode(child_state, (*self.steps, step))


class SearchGoal(Protocol):
    """只读取状态的精确停止条件。"""

    def reached(self, state: GeometryState) -> bool: ...


@dataclass(frozen=True, slots=True)
class PointGoal:
    """小问题回归使用的一个或多个精确目标点。"""

    points: tuple[Point, ...]
    require_all: bool = False

    def __init__(self, *points: Point, require_all: bool = False) -> None:
        if not points:
            raise ValueError("PointGoal 至少需要一个点")
        object.__setattr__(self, "points", tuple(points))
        object.__setattr__(self, "require_all", require_all)

    def reached(self, state: GeometryState) -> bool:
        results = tuple(state.contains_point(point) for point in self.points)
        return all(results) if self.require_all else any(results)


@dataclass(frozen=True, slots=True)
class Regular17Goal:
    """当前唯一 profile 的目标检测；目标点不会进入候选点集。"""

    require_both: bool = False

    def reached(self, state: GeometryState) -> bool:
        targets = reached_targets(state.points)
        return len(targets) == 2 if self.require_both else bool(targets)


@dataclass(frozen=True, slots=True)
class SearchStats:
    expanded_states: int
    generated_candidates: int
    accepted_states: int
    equivalent_pruned: int
    max_frontier: int
    heuristic_evaluations: int = 0
    heuristic_pruned: int = 0
    elapsed_seconds: float = 0.0
    candidate_generation_seconds: float = 0.0
    state_expansion_seconds: float = 0.0
    state_index_seconds: float = 0.0
    goal_test_seconds: float = 0.0
    heuristic_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    status: str
    node: SearchNode | None
    stats: SearchStats
    frontier: tuple[SearchNode, ...] = ()
