"""非锚定正 257 边形边目标的精确判定。

本模块有意不把坐标强制转换到 ``AA``。257 次分圆域的次数为 256，直接
对高次三角表达式反复做 ``AA`` 根隔离非常慢。调用方应传入同一精确数域中
的点、圆和一个本原 257 次单位根；研究验证器可使用 ``CyclotomicField``，
测试可使用 ``UniversalCyclotomicField``。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Protocol, TypeVar


POLYGON_SIDES = 257


class PointLike(Protocol):
    x: object
    y: object


class CircleLike(Protocol):
    center: PointLike
    radius_squared: object

    def contains(self, point: PointLike) -> bool: ...


PointT = TypeVar("PointT", bound=PointLike)


class InvalidPrimitiveRootError(ValueError):
    """目标判据收到的数不是本原 257 次单位根。"""


@lru_cache(maxsize=None)
def adjacent_trace(primitive_root):
    """返回 ``zeta + zeta^-1 = 2*cos(2*pi/257)``。

    257 是素数，所以非 1 的 257 次单位根必然本原。验证结果会按精确数域
    元素缓存，不在点对扫描的热点路径中重复做幂运算。
    """

    if primitive_root == 1 or primitive_root**POLYGON_SIDES != 1:
        raise InvalidPrimitiveRootError("需要一个本原 257 次单位根")
    return primitive_root + primitive_root**-1


def squared_distance(first: PointLike, second: PointLike):
    dx = first.x - second.x
    dy = first.y - second.y
    return dx * dx + dy * dy


def adjacent_chord_squared(circle: CircleLike, primitive_root):
    """返回该圆内接正 257 边形一条边的精确长度平方。"""

    # r^2 * (2 - zeta - zeta^-1)
    # = 2*r^2 * (1 - cos(2*pi/257)).
    return circle.radius_squared * (2 - adjacent_trace(primitive_root))


def is_target_pair(
    circle: CircleLike,
    first: PointLike,
    second: PointLike,
    primitive_root,
) -> bool:
    """判断两个状态点是否构成非锚定正 257 边形的一条边。"""

    return (
        first != second
        and circle.contains(first)
        and circle.contains(second)
        and squared_distance(first, second)
        == adjacent_chord_squared(circle, primitive_root)
    )


def first_target_pair(
    circle: CircleLike,
    points: Iterable[PointT],
    primitive_root,
) -> tuple[PointT, PointT] | None:
    """按输入顺序返回首个目标点对；不存在时返回 ``None``。"""

    ordered = tuple(points)
    for second_index, second in enumerate(ordered):
        for first in ordered[:second_index]:
            if is_target_pair(circle, first, second, primitive_root):
                return first, second
    return None
