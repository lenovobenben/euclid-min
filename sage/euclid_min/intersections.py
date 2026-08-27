"""直线与圆的全部精确交点及退化关系。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .exact import sqrt_nonnegative
from .geometry import Circle, Drawable, Line, Point


class IntersectionKind(str, Enum):
    """对象对的精确关系。"""

    ONE_POINT = "one_point"
    TWO_POINTS = "two_points"
    PARALLEL = "parallel"
    COINCIDENT = "coincident"
    DISJOINT = "disjoint"
    CONTAINED = "contained"
    TANGENT = "tangent"
    TANGENT_EXTERNAL = "tangent_external"
    TANGENT_INTERNAL = "tangent_internal"


@dataclass(frozen=True, slots=True)
class IntersectionResult:
    """一个对象对的关系和按精确字典序排列的有限实交点。"""

    kind: IntersectionKind
    points: tuple[Point, ...] = ()

    def __post_init__(self) -> None:
        ordered = tuple(sorted_unique_points(self.points))
        expected_count = {
            IntersectionKind.ONE_POINT: 1,
            IntersectionKind.TWO_POINTS: 2,
            IntersectionKind.PARALLEL: 0,
            IntersectionKind.COINCIDENT: 0,
            IntersectionKind.DISJOINT: 0,
            IntersectionKind.CONTAINED: 0,
            IntersectionKind.TANGENT: 1,
            IntersectionKind.TANGENT_EXTERNAL: 1,
            IntersectionKind.TANGENT_INTERNAL: 1,
        }[self.kind]
        if len(ordered) != expected_count:
            raise ValueError(
                f"交点关系 {self.kind.value} 应有 {expected_count} 个不同有限实交点，"
                f"实际为 {len(ordered)} 个"
            )
        object.__setattr__(self, "points", ordered)


def sorted_unique_points(points) -> list[Point]:
    """按 ``x``、再按 ``y`` 升序排序并按精确坐标去重。"""

    ordered = sorted(points)
    unique: list[Point] = []
    for point in ordered:
        if not unique or point != unique[-1]:
            unique.append(point)
    return unique


def intersect(first: Drawable, second: Drawable) -> IntersectionResult:
    """分派到三类精确求交函数；参数顺序不影响结果。"""

    if isinstance(first, Line) and isinstance(second, Line):
        return intersect_line_line(first, second)
    if isinstance(first, Line) and isinstance(second, Circle):
        return intersect_line_circle(first, second)
    if isinstance(first, Circle) and isinstance(second, Line):
        return intersect_line_circle(second, first)
    if isinstance(first, Circle) and isinstance(second, Circle):
        return intersect_circle_circle(first, second)
    raise TypeError("求交只支持 Line 和 Circle")


def intersect_line_line(first: Line, second: Line) -> IntersectionResult:
    """精确计算两条直线的关系。"""

    determinant = first.a * second.b - second.a * first.b
    if determinant == 0:
        if first == second:
            return IntersectionResult(IntersectionKind.COINCIDENT)
        return IntersectionResult(IntersectionKind.PARALLEL)

    x = (first.b * second.c - second.b * first.c) / determinant
    y = (first.c * second.a - second.c * first.a) / determinant
    return IntersectionResult(IntersectionKind.ONE_POINT, (Point(x, y),))


def intersect_line_circle(line: Line, circle: Circle) -> IntersectionResult:
    """精确计算直线和圆的 0、1 或 2 个有限实交点。"""

    center = circle.center
    norm_squared = line.a * line.a + line.b * line.b
    signed_numerator = line.a * center.x + line.b * center.y + line.c

    foot_x = center.x - line.a * signed_numerator / norm_squared
    foot_y = center.y - line.b * signed_numerator / norm_squared
    foot = Point(foot_x, foot_y)

    remaining_squared = (
        circle.radius_squared
        - signed_numerator * signed_numerator / norm_squared
    )

    if remaining_squared < 0:
        return IntersectionResult(IntersectionKind.DISJOINT)
    if remaining_squared == 0:
        return IntersectionResult(IntersectionKind.TANGENT, (foot,))

    scale = sqrt_nonnegative(remaining_squared / norm_squared)
    offset_x = -line.b * scale
    offset_y = line.a * scale
    points = (
        Point(foot.x + offset_x, foot.y + offset_y),
        Point(foot.x - offset_x, foot.y - offset_y),
    )
    return IntersectionResult(IntersectionKind.TWO_POINTS, points)


def intersect_circle_circle(first: Circle, second: Circle) -> IntersectionResult:
    """精确计算两个圆的全部关系和有限实交点。"""

    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    center_distance_squared = dx * dx + dy * dy

    if center_distance_squared == 0:
        if first.radius_squared == second.radius_squared:
            return IntersectionResult(IntersectionKind.COINCIDENT)
        return IntersectionResult(IntersectionKind.CONTAINED)

    center_distance = sqrt_nonnegative(center_distance_squared)
    first_radius = sqrt_nonnegative(first.radius_squared)
    second_radius = sqrt_nonnegative(second.radius_squared)
    radius_sum = first_radius + second_radius
    radius_difference = (
        first_radius - second_radius
        if first_radius >= second_radius
        else second_radius - first_radius
    )

    if center_distance > radius_sum:
        return IntersectionResult(IntersectionKind.DISJOINT)
    if center_distance < radius_difference:
        return IntersectionResult(IntersectionKind.CONTAINED)

    radical_axis = Line(
        2 * dx,
        2 * dy,
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius_squared
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius_squared,
    )
    points = intersect_line_circle(radical_axis, first).points

    if center_distance == radius_sum:
        return IntersectionResult(IntersectionKind.TANGENT_EXTERNAL, points)
    if center_distance == radius_difference:
        return IntersectionResult(IntersectionKind.TANGENT_INTERNAL, points)
    return IntersectionResult(IntersectionKind.TWO_POINTS, points)
