"""M257-8：删除最后两步后的单直线目标弦搜索。"""

from __future__ import annotations

from math import comb

from sage.all import ComplexBallField, RealBallField

from closure_target_audit import COSINE
from cyclotomic_replay import ORDER_FIELD
from full_intersection_closure import (
    build_runtime_arrangement,
    forward_full_closure,
)


BALL_PRECISION = 128
COMPLEX_BALL_FIELD = ComplexBallField(BALL_PRECISION)
REAL_BALL_FIELD = RealBallField(BALL_PRECISION)
TARGET_CHORD_DISTANCE_SQUARED = 2 * (1 + COSINE)
BALL_TARGET_CHORD_DISTANCE_SQUARED = 2 * (
    1 + COMPLEX_BALL_FIELD(COSINE).real()
)


def prepare_final_pair_line_universe(
    certificate: dict,
    full_report: dict,
    trace=None,
) -> dict:
    """恢复删除 68、69 步后可用于定义最后一条直线的精确点。"""

    arrangement = build_runtime_arrangement(certificate, trace=trace)
    paid_ids = [drawable["id"] for drawable in arrangement["drawables"]]
    removed = {"BG0", "target_transfer"}
    selected = set(paid_ids).difference(removed)
    closure = forward_full_closure(arrangement, selected)
    point_values = arrangement.pop("_runtime_point_values")
    available_items = [
        (point["id"], point_values[point["id"]])
        for point in arrangement["points"]
        if point["id"] in closure["available_points"]
        and point_values[point["id"]] is not None
    ]
    if closure["target_reached"]:
        raise ValueError("删除最后两步后不应在加入候选前命中目标")
    if len(closure["available_drawables"]) != 68:
        raise ValueError("删除最后两步后，前 67 个付费对象应全部可用")
    expected = full_report["summary"]["maximum_frontier_trials"][0]
    if expected["removed"] != ["BG0", "target_transfer"]:
        raise ValueError("M257-8 前沿报告的首选删二组合发生变化")
    if len(closure["available_points"]) != expected["available_points"]:
        raise ValueError("运行时闭包点数与前沿报告不一致")
    if len(available_items) != expected["available_exact_coordinate_points"]:
        raise ValueError("运行时精确点数与前沿报告不一致")
    return {
        "removed": ["BG0", "target_transfer"],
        "selected_paid_drawables": len(selected),
        "available_points": len(closure["available_points"]),
        "point_items": available_items,
        "line_definitions": comb(len(available_items), 2),
    }


def real_ball_point(point) -> tuple:
    """把精确实坐标严格嵌入 128 位实球。"""

    return (
        COMPLEX_BALL_FIELD(point.x).real(),
        COMPLEX_BALL_FIELD(point.y).real(),
    )


def serialize_ball_point(point: tuple) -> list[str]:
    return [str(point[0]), str(point[1])]


def deserialize_ball_point(value: list[str]) -> tuple:
    return REAL_BALL_FIELD(value[0]), REAL_BALL_FIELD(value[1])


def ball_line_chord_may_hit(first: tuple, second: tuple) -> bool:
    """严格实球尚不能排除目标弦等式时返回真。"""

    a = first[1] - second[1]
    b = second[0] - first[0]
    c = first[0] * second[1] - second[0] * first[1]
    # 全局坐标 y = 目标圆心坐标系中的 y - 1。
    d = c - b
    residual = (
        d * d
        - (a * a + b * b) * BALL_TARGET_CHORD_DISTANCE_SQUARED
    )
    return residual.contains_zero()


def exact_line_chord_hit(first, second) -> bool:
    """在通用分圆域中精确检查候选直线是否承载目标边。"""

    first_x = ORDER_FIELD(first.x)
    first_y = ORDER_FIELD(first.y)
    second_x = ORDER_FIELD(second.x)
    second_y = ORDER_FIELD(second.y)
    a = first_y - second_y
    b = second_x - first_x
    c = first_x * second_y - second_x * first_y
    d = c - b
    residual = (
        d * d
        - (a * a + b * b) * ORDER_FIELD(TARGET_CHORD_DISTANCE_SQUARED)
    )
    return residual == 0
