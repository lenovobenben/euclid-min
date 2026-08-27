"""Euclid-Min 的精确点、直线和圆。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
from typing import Any

from .exact import as_aa


class GeometryError(ValueError):
    """精确几何对象或操作不满足前置条件。"""


class CoincidentPointsError(GeometryError):
    """需要两个不同点的操作收到了同一个数学点。"""


class InvalidLineError(GeometryError):
    """直线系数没有定义一个有效欧氏直线。"""


class NonPositiveRadiusError(GeometryError):
    """圆的半径平方不是正数。"""


@total_ordering
@dataclass(frozen=True, slots=True)
class Point:
    """坐标属于 ``AA`` 的欧氏点。"""

    x: Any
    y: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", as_aa(self.x))
        object.__setattr__(self, "y", as_aa(self.y))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        if self.x != other.x:
            return self.x < other.x
        return self.y < other.y


@dataclass(frozen=True, slots=True)
class Line:
    """规范化方程 ``a*x + b*y + c = 0``。

    构造时把第一个非零的 ``a`` 或 ``b`` 精确归一化为 1，所以成比例的
    系数三元组会得到相同的数据类值。
    """

    a: Any
    b: Any
    c: Any

    def __post_init__(self) -> None:
        a = as_aa(self.a)
        b = as_aa(self.b)
        c = as_aa(self.c)
        if a == 0 and b == 0:
            raise InvalidLineError("直线系数 a 和 b 不能同时为零")

        scale = a if a != 0 else b
        object.__setattr__(self, "a", a / scale)
        object.__setattr__(self, "b", b / scale)
        object.__setattr__(self, "c", c / scale)

    @classmethod
    def through(cls, first: Point, second: Point) -> "Line":
        """返回通过两个不同点的唯一直线。"""

        if first == second:
            raise CoincidentPointsError("不能用同一个数学点画直线")
        return cls(
            first.y - second.y,
            second.x - first.x,
            first.x * second.y - second.x * first.y,
        )

    def contains(self, point: Point) -> bool:
        """精确判断点是否位于直线上。"""

        return self.a * point.x + self.b * point.y + self.c == 0


@dataclass(frozen=True, slots=True)
class Circle:
    """以精确圆心和正的半径平方表示的圆。"""

    center: Point
    radius_squared: Any

    def __post_init__(self) -> None:
        if not isinstance(self.center, Point):
            raise TypeError("圆心必须是 Point")
        radius_squared = as_aa(self.radius_squared)
        if radius_squared <= 0:
            raise NonPositiveRadiusError("圆的半径平方必须严格大于零")
        object.__setattr__(self, "radius_squared", radius_squared)

    @classmethod
    def through(cls, center: Point, point: Point) -> "Circle":
        """以 ``center`` 为圆心并经过另一个不同点构造圆。"""

        if center == point:
            raise CoincidentPointsError("圆心和圆上点不能是同一个数学点")
        dx = point.x - center.x
        dy = point.y - center.y
        return cls(center, dx * dx + dy * dy)

    def contains(self, point: Point) -> bool:
        """精确判断点是否位于圆上。"""

        dx = point.x - self.center.x
        dy = point.y - self.center.y
        return dx * dx + dy * dy == self.radius_squared


Drawable = Line | Circle
