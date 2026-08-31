"""从目标入射条件出发的反向搜索约束。"""

from __future__ import annotations

from ..target import TargetName, adjacent_targets
from .candidates import generate_candidates
from .model import Candidate, SearchStep
from ..state import GeometryState


def regular17_targets_on_step(step: SearchStep) -> tuple[TargetName, ...]:
    """精确返回一步新对象会与单位圆共同产生的允许目标。"""

    drawable = step.drawable()
    targets = adjacent_targets()
    return tuple(
        target_name
        for target_name in (TargetName.B_PLUS, TargetName.B_MINUS)
        if drawable.contains(targets[target_name])
    )


def is_regular17_terminal_step(step: SearchStep) -> bool:
    """判断该步是否可能作为首次命中目标的最后一步。"""

    return bool(regular17_targets_on_step(step))


def generate_regular17_terminal_candidates(
    state: GeometryState,
) -> tuple[Candidate, ...]:
    """从完整候选空间精确筛出经过任一允许目标的新对象。"""

    return tuple(
        candidate
        for candidate in generate_candidates(state)
        if is_regular17_terminal_step(candidate)
    )
