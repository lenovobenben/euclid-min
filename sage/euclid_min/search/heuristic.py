"""只用于排序或 beam 保留的非权威目标相关评分。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..geometry import Circle, Line, Point
from ..state import GeometryState
from ..target import adjacent_targets
from .model import Candidate


@dataclass(frozen=True, order=True, slots=True)
class HeuristicScore:
    """越小越优；任何字段都不能参与精确数学结论。"""

    incidence_residual: float
    point_distance_squared: float
    negative_point_count: int


@dataclass(frozen=True, order=True, slots=True)
class OneMoveHeuristicScore:
    """越小越优：首先衡量下一基础操作能否经过目标。"""

    next_drawable_residual: float
    point_distance_squared: float
    negative_point_count: int


@dataclass(frozen=True, order=True, slots=True)
class CandidateHeuristicScore:
    """越小越优：候选对象自身越接近经过目标越优。"""

    incidence_residual: float
    op_rank: int


class PointDistanceHeuristic:
    """按目标附近的点及近似通过目标的对象对排序状态。"""

    def __init__(self, *targets: Point) -> None:
        if not targets:
            raise ValueError("启发式至少需要一个目标点")
        self._targets = tuple(
            (float(target.x), float(target.y)) for target in targets
        )

    def evaluate(self, state: GeometryState) -> HeuristicScore:
        points = tuple(
            (float(point.x), float(point.y)) for point in state.points
        )
        point_distance_squared = min(
            (x - target_x) ** 2 + (y - target_y) ** 2
            for x, y in points
            for target_x, target_y in self._targets
        )

        incidence_residual = math.inf
        for target_x, target_y in self._targets:
            residuals = sorted(
                _incidence_residual(drawable, target_x, target_y)
                for drawable in state.drawables
            )
            if len(residuals) >= 2:
                incidence_residual = min(
                    incidence_residual,
                    residuals[0] + residuals[1],
                )
        return HeuristicScore(
            incidence_residual=incidence_residual,
            point_distance_squared=point_distance_squared,
            negative_point_count=-len(state.points),
        )


class Regular17Heuristic(PointDistanceHeuristic):
    """同时把两个镜像相邻顶点作为评分目标。"""

    def __init__(self) -> None:
        super().__init__(*adjacent_targets().values())


class OneMoveTargetHeuristic:
    """按“再画一个对象即可命中目标”的数值残差排序状态。

    评分枚举当前点对可定义的全部直线和有向圆，但只做浮点计算。它只用于
    非证明 beam search 的保留顺序；成功仍由精确目标检测与独立 verifier
    决定。
    """

    def __init__(self, *targets: Point) -> None:
        if not targets:
            raise ValueError("启发式至少需要一个目标点")
        self._targets = tuple(
            (float(target.x), float(target.y)) for target in targets
        )

    def evaluate(self, state: GeometryState) -> OneMoveHeuristicScore:
        points = tuple(
            (float(point.x), float(point.y)) for point in state.points
        )
        existing_lines = {
            _line_signature(float(line.a), float(line.b), float(line.c))
            for line in state.lines
        }
        existing_circles = {
            _circle_signature(
                float(circle.center.x),
                float(circle.center.y),
                float(circle.radius_squared),
            )
            for circle in state.circles
        }
        point_distance_squared = min(
            (x - target_x) ** 2 + (y - target_y) ** 2
            for x, y in points
            for target_x, target_y in self._targets
        )
        next_drawable_residual = math.inf
        for first_index, (first_x, first_y) in enumerate(points):
            for second_x, second_y in points[first_index + 1 :]:
                dx = second_x - first_x
                dy = second_y - first_y
                denominator = math.hypot(dx, dy)
                if denominator != 0.0:
                    a = first_y - second_y
                    b = second_x - first_x
                    c = first_x * second_y - second_x * first_y
                    scale = a if a != 0.0 else b
                    if _line_signature(
                        a / scale,
                        b / scale,
                        c / scale,
                    ) in existing_lines:
                        continue
                    for target_x, target_y in self._targets:
                        residual = abs(
                            dx * (target_y - first_y)
                            - dy * (target_x - first_x)
                        ) / denominator
                        next_drawable_residual = min(
                            next_drawable_residual,
                            residual,
                        )

        for center_x, center_y in points:
            for through_x, through_y in points:
                if center_x == through_x and center_y == through_y:
                    continue
                radius_squared = (
                    (through_x - center_x) ** 2
                    + (through_y - center_y) ** 2
                )
                if _circle_signature(
                    center_x,
                    center_y,
                    radius_squared,
                ) in existing_circles:
                    continue
                for target_x, target_y in self._targets:
                    target_radius_squared = (
                        (target_x - center_x) ** 2
                        + (target_y - center_y) ** 2
                    )
                    residual = abs(
                        target_radius_squared - radius_squared
                    ) / max(1.0, abs(radius_squared))
                    next_drawable_residual = min(
                        next_drawable_residual,
                        residual,
                    )

        return OneMoveHeuristicScore(
            next_drawable_residual=next_drawable_residual,
            point_distance_squared=point_distance_squared,
            negative_point_count=-len(points),
        )


class Regular17OneMoveHeuristic(OneMoveTargetHeuristic):
    """同时针对两个镜像目标评估下一基础操作。"""

    def __init__(self) -> None:
        super().__init__(*adjacent_targets().values())


class TargetCandidateHeuristic:
    """在精确展开前，以候选对象对目标的浮点残差排序。"""

    def __init__(
        self,
        *targets: Point,
        max_input_level: int | None = None,
    ) -> None:
        if not targets:
            raise ValueError("候选启发式至少需要一个目标点")
        if max_input_level is not None and max_input_level < 0:
            raise ValueError("输入点生成层级上限不能为负数")
        self._targets = tuple(
            (float(target.x), float(target.y)) for target in targets
        )
        self._max_input_level = max_input_level
        self._point_level_cache: dict[int, tuple[Point, int]] = {}
        self._point_float_cache: dict[
            int, tuple[Point, tuple[float, float]]
        ] = {}
        self._existing_operation_keys: set[tuple] = set()

    def prepare_state(self, state: GeometryState) -> None:
        """缓存当前状态的廉价点生成层级，供热路径 O(1) 查询。"""

        self._point_level_cache = {
            id(point): (point, level)
            for point, level in zip(state.points, state.point_levels)
        }
        self._point_float_cache = {
            id(point): (point, (float(point.x), float(point.y)))
            for point in state.points
        }
        self._existing_operation_keys = {
            (
                "line",
                *_line_signature(
                    float(line.a),
                    float(line.b),
                    float(line.c),
                ),
            )
            for line in state.lines
        }
        self._existing_operation_keys.update(
            (
                "circle",
                *_circle_signature(
                    float(circle.center.x),
                    float(circle.center.y),
                    float(circle.radius_squared),
                ),
            )
            for circle in state.circles
        )

    def evaluate(
        self,
        _state: GeometryState,
        candidate: Candidate,
    ) -> CandidateHeuristicScore | None:
        return self.evaluate_points(
            candidate.op,
            candidate.first,
            candidate.second,
        )

    def evaluate_points(
        self,
        op: str,
        first: Point,
        second: Point,
    ) -> CandidateHeuristicScore | None:
        if self._max_input_level is not None and max(
            self._point_level(first),
            self._point_level(second),
        ) > self._max_input_level:
            return None
        first_x, first_y = self._point_coordinates(first)
        second_x, second_y = self._point_coordinates(second)
        if self.operation_key(op, first, second) in self._existing_operation_keys:
            return None
        if op == "line":
            dx = second_x - first_x
            dy = second_y - first_y
            denominator = math.hypot(dx, dy)
            residual = (
                min(
                    abs(
                        dx * (target_y - first_y)
                        - dy * (target_x - first_x)
                    ) / denominator
                    for target_x, target_y in self._targets
                )
                if denominator != 0.0
                else math.inf
            )
        elif op == "circle":
            radius_squared = (
                (second_x - first_x) ** 2
                + (second_y - first_y) ** 2
            )
            residual = min(
                abs(
                    (target_x - first_x) ** 2
                    + (target_y - first_y) ** 2
                    - radius_squared
                ) / max(1.0, abs(radius_squared))
                for target_x, target_y in self._targets
            )
        else:
            raise ValueError(f"不支持的候选操作 {op!r}")
        return CandidateHeuristicScore(
            incidence_residual=residual,
            op_rank=0 if op == "line" else 1,
        )

    def operation_key(
        self,
        op: str,
        first: Point,
        second: Point,
    ) -> tuple:
        first_x, first_y = self._point_coordinates(first)
        second_x, second_y = self._point_coordinates(second)
        if op == "line":
            a = first_y - second_y
            b = second_x - first_x
            c = first_x * second_y - second_x * first_y
            if a == 0.0 and b == 0.0:
                return ("line-float-collision", id(first), id(second))
            scale = a if a != 0.0 else b
            return (
                "line",
                *_line_signature(a / scale, b / scale, c / scale),
            )
        if op == "circle":
            radius_squared = (
                (second_x - first_x) ** 2
                + (second_y - first_y) ** 2
            )
            return (
                "circle",
                *_circle_signature(first_x, first_y, radius_squared),
            )
        raise ValueError(f"不支持的候选操作 {op!r}")

    def _point_level(self, point: Point) -> int:
        cache_key = id(point)
        cached = self._point_level_cache.get(cache_key)
        if cached is not None and cached[0] is point:
            return cached[1]
        raise ValueError("候选评分前必须先 prepare_state")

    def operation_level(self, _op: str, first: Point, second: Point) -> int:
        """返回两个输入点的最高生成层级，作为廉价成本代理。"""

        return max(self._point_level(first), self._point_level(second))

    def _point_coordinates(self, point: Point) -> tuple[float, float]:
        cache_key = id(point)
        cached = self._point_float_cache.get(cache_key)
        if cached is not None and cached[0] is point:
            return cached[1]
        coordinates = (float(point.x), float(point.y))
        self._point_float_cache[cache_key] = (point, coordinates)
        return coordinates


class Regular17CandidateHeuristic(TargetCandidateHeuristic):
    """同时针对两个镜像目标预排序待展开候选。"""

    def __init__(self, *, max_input_level: int | None = None) -> None:
        super().__init__(
            *adjacent_targets().values(),
            max_input_level=max_input_level,
        )


def _line_signature(a: float, b: float, c: float) -> tuple[float, ...]:
    return (round(a, 12), round(b, 12), round(c, 12))


def _circle_signature(
    center_x: float,
    center_y: float,
    radius_squared: float,
) -> tuple[float, ...]:
    return (
        round(center_x, 12),
        round(center_y, 12),
        round(radius_squared, 12),
    )


def _incidence_residual(drawable, x: float, y: float) -> float:
    if isinstance(drawable, Line):
        a = float(drawable.a)
        b = float(drawable.b)
        c = float(drawable.c)
        return abs(a * x + b * y + c) / math.hypot(a, b)
    if isinstance(drawable, Circle):
        center_x = float(drawable.center.x)
        center_y = float(drawable.center.y)
        radius_squared = float(drawable.radius_squared)
        residual = (x - center_x) ** 2 + (y - center_y) ** 2 - radius_squared
        return abs(residual) / max(1.0, abs(radius_squared))
    raise TypeError("启发式只支持直线和圆")
