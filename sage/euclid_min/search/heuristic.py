"""只用于排序或 beam 保留的非权威目标相关评分。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..geometry import Circle, Line, Point
from ..state import GeometryState
from ..target import adjacent_targets


@dataclass(frozen=True, order=True, slots=True)
class HeuristicScore:
    """越小越优；任何字段都不能参与精确数学结论。"""

    incidence_residual: float
    point_distance_squared: float
    negative_point_count: int


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
