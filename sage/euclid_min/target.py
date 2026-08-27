"""正十七边形两个相邻目标点的精确定义。"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from types import MappingProxyType
from typing import Iterable, Mapping

from sage.all import AA, cos, pi, sin

from .geometry import Drawable, Point


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


def reached_targets_by_object_pair(
    first: Drawable,
    second: Drawable,
) -> tuple[TargetName, ...]:
    """精确返回作为两个不同对象公共点出现的目标。

    两条不同直线、两个不同圆或一线一圆不可能共享一段曲线。因此同时满足
    两个对象方程的目标点，恰好是自动闭包会产生的有限孤立交点；无需先求出
    该对象对的其他交点。
    """

    if type(first) is type(second) and first == second:
        return ()
    targets = adjacent_targets()
    return tuple(
        name
        for name in (TargetName.B_PLUS, TargetName.B_MINUS)
        if first.contains(targets[name]) and second.contains(targets[name])
    )
