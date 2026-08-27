"""实代数数的最小适配层。

M1 的权威数域固定为 SageMath Algebraic Real Field ``AA``。这个模块集中
放置强制转换和比较，避免几何代码意外退回 Python float。
"""

from __future__ import annotations

from typing import Any

from sage.all import AA


class InexactInputError(TypeError):
    """精确内核收到了 Python 浮点数等非精确输入。"""


def as_aa(value: Any):
    """把输入精确转换到 ``AA``。

    无法精确解释的值由 SageMath 抛出异常；调用方不得用浮点容差兜底。
    """

    if isinstance(value, float):
        raise InexactInputError(
            "精确内核不接受 Python float；请使用整数、有理数或精确代数表达式"
        )
    return AA(value)


def compare(left: Any, right: Any) -> int:
    """返回两个实代数数的精确三向比较结果。"""

    left_aa = as_aa(left)
    right_aa = as_aa(right)
    if left_aa < right_aa:
        return -1
    if left_aa > right_aa:
        return 1
    return 0


def sqrt_nonnegative(value: Any):
    """返回非负实代数数的精确平方根。"""

    value_aa = as_aa(value)
    if value_aa < 0:
        raise ValueError("不能在实代数数域中对负数开平方")
    return value_aa.sqrt()
