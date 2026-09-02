"""M257-8：给最大前沿中的抽象残余交点构造严格实球包围。"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from sage.all import ComplexBallField, RealBallField

from cyclotomic_replay import ORDER_FIELD, Circle, Line
from full_intersection_closure import (
    build_runtime_arrangement,
    forward_full_closure,
)


BALL_PRECISION = 128
COMPLEX_BALL_FIELD = ComplexBallField(BALL_PRECISION)
REAL_BALL_FIELD = RealBallField(BALL_PRECISION)


def _real_ball(value):
    return COMPLEX_BALL_FIELD(value).real()


def exact_point_ball(point) -> tuple:
    return _real_ball(point.x), _real_ball(point.y)


def serialize_ball_point(point: tuple) -> list[str]:
    return [str(point[0]), str(point[1])]


def deserialize_ball_point(value: list[str]) -> tuple:
    return REAL_BALL_FIELD(value[0]), REAL_BALL_FIELD(value[1])


def balls_may_overlap(first: tuple, second: tuple) -> bool:
    return (first[0] - second[0]).contains_zero() and (
        first[1] - second[1]
    ).contains_zero()


def line_circle_intersection_balls(
    coefficients: tuple,
    circle: Circle,
) -> list[tuple]:
    """严格包围一条精确直线与一个精确圆的全部有限实交点。"""

    a, b, c = coefficients
    norm_squared = a * a + b * b
    signed = a * circle.center.x + b * circle.center.y + c
    discriminant = circle.radius_squared * norm_squared - signed * signed
    ordered_discriminant = ORDER_FIELD(discriminant)
    if ordered_discriminant < 0:
        return []

    foot_x = circle.center.x - a * signed / norm_squared
    foot_y = circle.center.y - b * signed / norm_squared
    foot = (_real_ball(foot_x), _real_ball(foot_y))
    if ordered_discriminant == 0:
        return [foot]

    # abs 不改变真实的正判别式；若嵌入区间因舍入略微跨过 0，abs 可安全地
    # 把它收缩到 sqrt 的定义域，而不会丢失真实值。
    root = abs(_real_ball(discriminant)).sqrt()
    scale = root / _real_ball(norm_squared)
    offset_x = -_real_ball(b) * scale
    offset_y = _real_ball(a) * scale
    return [
        (foot[0] - offset_x, foot[1] - offset_y),
        (foot[0] + offset_x, foot[1] + offset_y),
    ]


def circle_circle_intersection_balls(
    first: Circle,
    second: Circle,
) -> list[tuple]:
    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    if dx == 0 and dy == 0:
        return []
    radical_axis = (
        2 * dx,
        2 * dy,
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius_squared
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius_squared,
    )
    return line_circle_intersection_balls(radical_axis, first)


def _producer_pair(point: dict, drawable_values: dict) -> tuple[str, str]:
    lines = [
        name
        for name in point["incident_drawables"]
        if isinstance(drawable_values[name], Line)
    ]
    circles = [
        name
        for name in point["incident_drawables"]
        if isinstance(drawable_values[name], Circle)
    ]
    if point["origin"] == "line_circle_residual":
        if len(lines) != 1 or len(circles) != 1:
            raise ValueError(
                f"残余点 {point['id']} 无法唯一恢复直线—圆生产者"
            )
        return lines[0], circles[0]
    if point["origin"] == "circle_circle_residual":
        if lines or len(circles) != 2:
            raise ValueError(
                f"残余点 {point['id']} 无法唯一恢复圆—圆生产者"
            )
        return circles[0], circles[1]
    raise ValueError(f"点 {point['id']} 不是抽象残余交点")


def prepare_maximum_frontier_ball_universe(
    certificate: dict,
    frontier_report: dict,
    trace=None,
) -> dict:
    """恢复最大前沿，并为全部可用点构造严格且互不重叠的实球。"""

    arrangement = build_runtime_arrangement(certificate, trace=trace)
    point_values = arrangement.pop("_runtime_point_values")
    drawable_values = arrangement.pop("_runtime_drawable_values")
    paid_ids = [drawable["id"] for drawable in arrangement["drawables"]]
    removed = {"BG0", "target_transfer"}
    selected = set(paid_ids).difference(removed)
    closure = forward_full_closure(arrangement, selected)
    expected = frontier_report["summary"]["maximum_frontier_trials"][0]
    if expected["removed"] != ["BG0", "target_transfer"]:
        raise ValueError("候选前沿首项发生变化")

    available_records = [
        point
        for point in arrangement["points"]
        if point["id"] in closure["available_points"]
    ]
    exact_records = [
        point for point in available_records if point_values[point["id"]] is not None
    ]
    abstract_records = [
        point for point in available_records if point_values[point["id"]] is None
    ]
    if len(available_records) != expected["available_points"]:
        raise ValueError("最大前沿可用点数不一致")
    if len(exact_records) != expected["available_exact_coordinate_points"]:
        raise ValueError("最大前沿精确点数不一致")

    point_balls = {
        point["id"]: exact_point_ball(point_values[point["id"]])
        for point in exact_records
    }
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for point in abstract_records:
        first_name, second_name = _producer_pair(point, drawable_values)
        groups[(point["origin"], first_name, second_name)].append(point)

    group_summaries = []
    for (origin, first_name, second_name), records in groups.items():
        first = drawable_values[first_name]
        second = drawable_values[second_name]
        if origin == "line_circle_residual":
            roots = line_circle_intersection_balls(
                (first.a, first.b, first.c),
                second,
            )
        else:
            roots = circle_circle_intersection_balls(first, second)

        materialized = [
            point
            for point in arrangement["points"]
            if point_values[point["id"]] is not None
            and first_name in point["incident_drawables"]
            and second_name in point["incident_drawables"]
        ]
        remaining = list(roots)
        for point in materialized:
            exact_ball = exact_point_ball(point_values[point["id"]])
            matches = [
                index
                for index, root in enumerate(remaining)
                if balls_may_overlap(root, exact_ball)
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"生产者 {first_name}/{second_name} 的已物化分支无法唯一匹配"
                )
            remaining.pop(matches[0])
        if len(remaining) != len(records):
            raise ValueError(
                f"生产者 {first_name}/{second_name} 的残余分支数量不一致"
            )
        ordered_roots = sorted(
            remaining,
            key=lambda point: (
                float(point[0].center()),
                float(point[1].center()),
            ),
        )
        for record, root in zip(sorted(records, key=lambda item: item["id"]), ordered_roots):
            point_balls[record["id"]] = root
        group_summaries.append(
            {
                "origin": origin,
                "producer": [first_name, second_name],
                "materialized_branches": len(materialized),
                "residual_branches": len(records),
            }
        )

    ordered_items = [
        (point["id"], point_balls[point["id"]]) for point in available_records
    ]
    ambiguous_pairs = []
    for (first_name, first), (second_name, second) in combinations(ordered_items, 2):
        if balls_may_overlap(first, second):
            ambiguous_pairs.append([first_name, second_name])
            if len(ambiguous_pairs) >= 20:
                break

    incidence_checks = 0
    failed_incidences = []
    for point in available_records:
        x, y = point_balls[point["id"]]
        for drawable_name in point["incident_drawables"]:
            drawable = drawable_values[drawable_name]
            if isinstance(drawable, Line):
                residual = (
                    _real_ball(drawable.a) * x
                    + _real_ball(drawable.b) * y
                    + _real_ball(drawable.c)
                )
            else:
                dx = x - _real_ball(drawable.center.x)
                dy = y - _real_ball(drawable.center.y)
                residual = (
                    dx * dx
                    + dy * dy
                    - _real_ball(drawable.radius_squared)
                )
            incidence_checks += 1
            if not residual.contains_zero():
                failed_incidences.append([point["id"], drawable_name])

    return {
        "removed": ["BG0", "target_transfer"],
        "available_points": len(available_records),
        "exact_points": len(exact_records),
        "abstract_points": len(abstract_records),
        "abstract_origin_counts": {
            origin: sum(point["origin"] == origin for point in abstract_records)
            for origin in ("line_circle_residual", "circle_circle_residual")
        },
        "producer_groups": sorted(
            group_summaries,
            key=lambda item: (item["origin"], item["producer"]),
        ),
        "point_items": ordered_items,
        "incidence_checks": incidence_checks,
        "failed_incidences": failed_incidences,
        "ambiguous_point_pairs": ambiguous_pairs,
    }
