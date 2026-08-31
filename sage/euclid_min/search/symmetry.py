"""固定 profile 关于横轴反射的精确对象和状态作用。"""

from __future__ import annotations

from ..geometry import Circle, Drawable, Line, Point
from ..state import GeometryState


def reflect_point_horizontal(point: Point) -> Point:
    """返回点在横轴反射下的像。"""

    return Point(point.x, -point.y)


def reflect_line_horizontal(line: Line) -> Line:
    """返回直线在横轴反射下的像，并重新执行精确规范化。"""

    return Line(line.a, -line.b, line.c)


def reflect_circle_horizontal(circle: Circle) -> Circle:
    """返回圆在横轴反射下的像。"""

    return Circle(
        reflect_point_horizontal(circle.center),
        circle.radius_squared,
    )


def reflect_drawable_horizontal(drawable: Drawable) -> Drawable:
    if isinstance(drawable, Line):
        return reflect_line_horizontal(drawable)
    return reflect_circle_horizontal(drawable)


def states_equal_under_horizontal_reflection(
    first: GeometryState,
    second: GeometryState,
) -> bool:
    """精确判断 ``first`` 的横轴镜像是否等于 ``second``。"""

    return (
        _sets_equal(
            tuple(reflect_point_horizontal(point) for point in first.points),
            second.points,
        )
        and _sets_equal(
            tuple(reflect_line_horizontal(line) for line in first.lines),
            second.lines,
        )
        and _sets_equal(
            tuple(
                reflect_circle_horizontal(circle) for circle in first.circles
            ),
            second.circles,
        )
    )


def _sets_equal(first: tuple, second: tuple) -> bool:
    if len(first) != len(second):
        return False
    return all(any(item == candidate for candidate in second) for item in first)
