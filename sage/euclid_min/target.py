"""正十七边形两个相邻目标点的精确定义。"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from types import MappingProxyType
from typing import Iterable, Mapping

from sage.all import AA, cos, pi, sin

from .geometry import Point


class TargetName(str, Enum):
    B_PLUS = "B_plus"
    B_MINUS = "B_minus"


@lru_cache(maxsize=1)
def adjacent_targets() -> Mapping[TargetName, Point]:
    """返回 (A=(1,0)) 的两个精确正十七边形相邻顶点。"""

    x = AA(cos(2 * pi / 17))
    y = AA(sin(2 * pi / 17))
    return MappingProxyType(
        {
            TargetName.B_PLUS: Point(x, y),
            TargetName.B_MINUS: Point(x, -y),
        }
    )


def reached_targets(points: Iterable[Point]) -> tuple[TargetName, ...]:
    """精确返回给定点集中出现的目标，顺序固定为正、负方向。"""

    point_list = tuple(points)
    targets = adjacent_targets()
    return tuple(
        name
        for name in (TargetName.B_PLUS, TargetName.B_MINUS)
        if any(point == targets[name] for point in point_list)
    )
