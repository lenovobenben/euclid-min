"""M257-8：最后一个新圆的两类直接目标搜索。"""

from __future__ import annotations

from cyclotomic_replay import ORDER_FIELD
from final_pair_line_adjacent_search import (
    ball_candidate_may_reach_existing,
    exact_candidate_reaches_existing,
)
from final_pair_line_chord_search import (
    BALL_TARGET_CHORD_DISTANCE_SQUARED,
    TARGET_CHORD_DISTANCE_SQUARED,
)


def ball_circle_carrier(center: tuple, through: tuple) -> tuple:
    """返回候选圆与目标圆根轴的严格实球系数。"""

    center_x = center[0]
    center_y = center[1] + 1
    radius_dx = center[0] - through[0]
    radius_dy = center[1] - through[1]
    radius_squared = radius_dx * radius_dx + radius_dy * radius_dy
    return (
        -2 * center_x,
        -2 * center_y,
        center_x * center_x
        + center_y * center_y
        - radius_squared
        + 4,
    )


def exact_circle_carrier(center, through) -> tuple:
    center_x = ORDER_FIELD(center.x)
    center_y_global = ORDER_FIELD(center.y)
    center_y = center_y_global + 1
    through_x = ORDER_FIELD(through.x)
    through_y = ORDER_FIELD(through.y)
    radius_dx = center_x - through_x
    radius_dy = center_y_global - through_y
    radius_squared = radius_dx * radius_dx + radius_dy * radius_dy
    return (
        -2 * center_x,
        -2 * center_y,
        center_x * center_x
        + center_y * center_y
        - radius_squared
        + 4,
    )


def ball_circle_self_chord_may_hit(carrier: tuple) -> bool:
    a, b, d = carrier
    residual = (
        d * d
        - (a * a + b * b) * BALL_TARGET_CHORD_DISTANCE_SQUARED
    )
    return residual.contains_zero()


def exact_circle_self_chord_hit(carrier: tuple) -> bool:
    a, b, d = carrier
    if a == 0 and b == 0:
        # 与目标圆同心；尤其重画 c0 不产生新的公共点。
        return False
    return (
        d * d
        == (a * a + b * b) * ORDER_FIELD(TARGET_CHORD_DISTANCE_SQUARED)
    )


def ball_circle_candidate_may_hit(
    carrier: tuple,
    existing_carriers: list[tuple],
) -> tuple[bool, int]:
    if ball_circle_self_chord_may_hit(carrier):
        return True, 1
    may_hit, checks = ball_candidate_may_reach_existing(
        carrier,
        existing_carriers,
    )
    return may_hit, checks + 1


def exact_circle_candidate_hits(
    carrier: tuple,
    existing_carriers: list[tuple],
) -> list[dict]:
    a, b, _d = carrier
    if a == 0 and b == 0:
        return []
    hits = []
    if exact_circle_self_chord_hit(carrier):
        hits.append({"source": "candidate", "orientation": "self_chord"})
    hits.extend(exact_candidate_reaches_existing(carrier, existing_carriers))
    return hits
