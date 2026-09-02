"""M257-8：最后一条新直线与既有目标圆点的邻接搜索。"""

from __future__ import annotations

from sage.all import ComplexBallField

from closure_target_audit import COSINE
from cyclotomic_replay import (
    FIELD,
    ORDER_FIELD,
    Circle,
    Line,
)
from full_intersection_closure import (
    build_runtime_arrangement,
    forward_full_closure,
)


BALL_PRECISION = 128
BALL_FIELD = ComplexBallField(BALL_PRECISION)
ORDER_ZETA = ORDER_FIELD(FIELD.gen())
ORDER_COSINE = ORDER_FIELD(COSINE)
ORDER_SINE = (ORDER_ZETA - ORDER_ZETA**-1) / (2 * ORDER_FIELD.gen(4))
BALL_COSINE = BALL_FIELD(ORDER_COSINE).real()
BALL_SINE = BALL_FIELD(ORDER_SINE).real()
TARGET_RADIUS_SQUARED = ORDER_FIELD(4)


def _exact_line_carrier(first, second) -> tuple:
    first_x = ORDER_FIELD(first.x)
    first_y = ORDER_FIELD(first.y)
    second_x = ORDER_FIELD(second.x)
    second_y = ORDER_FIELD(second.y)
    a = first_y - second_y
    b = second_x - first_x
    c = first_x * second_y - second_x * first_y
    return a, b, c - b


def ball_line_carrier(first: tuple, second: tuple) -> tuple:
    a = first[1] - second[1]
    b = second[0] - first[0]
    c = first[0] * second[1] - second[0] * first[1]
    return a, b, c - b


def target_carrier(drawable, target_circle: Circle) -> tuple | None:
    """返回目标圆心坐标系中的未规范化弦载线。"""

    if isinstance(drawable, Line):
        return (
            ORDER_FIELD(drawable.a),
            ORDER_FIELD(drawable.b),
            ORDER_FIELD(drawable.c - drawable.b),
        )
    if not isinstance(drawable, Circle):
        raise TypeError("只支持直线和圆")
    if drawable == target_circle:
        return None
    center_x = ORDER_FIELD(drawable.center.x - target_circle.center.x)
    center_y = ORDER_FIELD(drawable.center.y - target_circle.center.y)
    radius_squared = ORDER_FIELD(drawable.radius_squared)
    target_radius_squared = ORDER_FIELD(target_circle.radius_squared)
    return (
        -2 * center_x,
        -2 * center_y,
        center_x * center_x
        + center_y * center_y
        - radius_squared
        + target_radius_squared,
    )


def carrier_has_real_target_point(carrier: tuple) -> bool:
    a, b, d = carrier
    discriminant = TARGET_RADIUS_SQUARED * (a * a + b * b) - d * d
    return discriminant >= 0


def ball_carrier(carrier: tuple) -> tuple:
    return tuple(BALL_FIELD(value).real() for value in carrier)


def _rotate_carrier(carrier: tuple, orientation: int, cosine, sine) -> tuple:
    a, b, d = carrier
    return (
        a * cosine - orientation * b * sine,
        b * cosine + orientation * a * sine,
        d,
    )


def _homogeneous_intersection(first: tuple, second: tuple) -> tuple:
    first_a, first_b, first_d = first
    second_a, second_b, second_d = second
    return (
        first_b * second_d - second_b * first_d,
        first_d * second_a - second_d * first_a,
        first_a * second_b - second_a * first_b,
    )


def ball_carriers_may_have_adjacent_points(
    source: tuple,
    destination: tuple,
    orientation: int,
) -> bool:
    rotated = _rotate_carrier(
        source,
        orientation,
        BALL_COSINE,
        BALL_SINE,
    )
    x, y, w = _homogeneous_intersection(rotated, destination)
    residual = x * x + y * y - 4 * w * w
    return residual.contains_zero()


def exact_carriers_have_adjacent_points(
    source: tuple,
    destination: tuple,
    orientation: int,
) -> bool:
    rotated = _rotate_carrier(
        source,
        orientation,
        ORDER_COSINE,
        ORDER_SINE,
    )
    x, y, w = _homogeneous_intersection(rotated, destination)
    if w != 0:
        return x * x + y * y == TARGET_RADIUS_SQUARED * w * w
    if x != 0 or y != 0:
        return False
    return carrier_has_real_target_point(destination)


def ball_carrier_may_contain_initial_neighbor(
    destination: tuple,
    orientation: int,
) -> bool:
    a, b, d = destination
    x = -orientation * 2 * BALL_SINE
    y = 2 * BALL_COSINE
    return (a * x + b * y + d).contains_zero()


def exact_carrier_contains_initial_neighbor(
    destination: tuple,
    orientation: int,
) -> bool:
    a, b, d = destination
    x = -orientation * 2 * ORDER_SINE
    y = 2 * ORDER_COSINE
    return a * x + b * y + d == 0


def ball_candidate_may_reach_existing(
    destination: tuple,
    existing_carriers: list[tuple],
) -> tuple[bool, int]:
    relation_checks = 0
    for orientation in (-1, 1):
        relation_checks += 1
        if ball_carrier_may_contain_initial_neighbor(destination, orientation):
            return True, relation_checks
    for source in existing_carriers:
        for orientation in (-1, 1):
            relation_checks += 1
            if ball_carriers_may_have_adjacent_points(
                source,
                destination,
                orientation,
            ):
                return True, relation_checks
    return False, relation_checks


def exact_candidate_reaches_existing(
    destination: tuple,
    existing_carriers: list[tuple],
) -> list[dict]:
    hits = []
    for orientation in (-1, 1):
        if exact_carrier_contains_initial_neighbor(destination, orientation):
            hits.append(
                {
                    "source": "B",
                    "orientation": orientation,
                }
            )
    for source_name, source in existing_carriers:
        for orientation in (-1, 1):
            if exact_carriers_have_adjacent_points(
                source,
                destination,
                orientation,
            ):
                hits.append(
                    {
                        "source": source_name,
                        "orientation": orientation,
                    }
                )
    return hits


def prepare_final_pair_adjacent_universe(
    certificate: dict,
    frontier_report: dict,
    trace=None,
) -> dict:
    arrangement = build_runtime_arrangement(certificate, trace=trace)
    point_values = arrangement.pop("_runtime_point_values")
    drawable_values = arrangement.pop("_runtime_drawable_values")
    paid_ids = [drawable["id"] for drawable in arrangement["drawables"]]
    removed = {"BG0", "target_transfer"}
    selected = set(paid_ids).difference(removed)
    closure = forward_full_closure(arrangement, selected)
    point_items = [
        (point["id"], point_values[point["id"]])
        for point in arrangement["points"]
        if point["id"] in closure["available_points"]
        and point_values[point["id"]] is not None
    ]
    target_circle = drawable_values["c0"]
    existing_carriers = []
    for name in paid_ids:
        if name not in closure["available_drawables"]:
            continue
        carrier = target_carrier(drawable_values[name], target_circle)
        if carrier is not None and carrier_has_real_target_point(carrier):
            existing_carriers.append((name, carrier))
    expected = frontier_report["summary"]["maximum_frontier_trials"][0]
    if expected["removed"] != ["BG0", "target_transfer"]:
        raise ValueError("候选前沿首项发生变化")
    if len(point_items) != expected["available_exact_coordinate_points"]:
        raise ValueError("精确定义点数与候选前沿不一致")
    if len(closure["available_points"]) != expected["available_points"]:
        raise ValueError("闭包点数与候选前沿不一致")
    if len(closure["available_drawables"]) != 68:
        raise ValueError("前 67 个付费对象没有全部进入闭包")
    return {
        "removed": ["BG0", "target_transfer"],
        "available_points": len(closure["available_points"]),
        "point_items": point_items,
        "existing_target_carriers": existing_carriers,
    }


def exact_line_carrier(first, second) -> tuple:
    return _exact_line_carrier(first, second)
