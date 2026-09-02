"""69E 证书交点的精确代数 proof hints。

Proof hint 只提供候选点；重放器仍会精确检查候选点属于证书声明的两个对象，
并用另一交点的弦中点反射式核对字典序索引。候选坐标不写入证书。
"""

from __future__ import annotations

from cyclotomic_replay import FIELD, ORDER_FIELD, Point
from verify_69e import verify


def build_proof_hints() -> dict[str, Point]:
    replay = verify()[0]
    hints = {
        name: Point(FIELD(point.x), FIELD(point.y))
        for name, point in replay.points.items()
    }

    sqrt_three = ORDER_FIELD(3).sqrt()
    if sqrt_three < 0:
        sqrt_three = -sqrt_three
    hints["q_c0_left"] = Point(-sqrt_three, 0)
    hints["q_c0_right"] = Point(sqrt_three, 0)

    zeta = ORDER_FIELD.gen(257)
    imaginary_unit = ORDER_FIELD.gen(4)
    target_x = zeta + zeta**-1
    target_y_offset = (zeta - zeta**-1) / imaginary_unit
    if target_y_offset < 0:
        target_y_offset = -target_y_offset
    hints["W2_minus"] = Point(target_x, -1 - target_y_offset)
    hints["W2_plus"] = Point(target_x, -1 + target_y_offset)
    return hints
