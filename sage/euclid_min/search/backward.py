"""从目标入射条件出发的反向搜索约束。"""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Drawable, Point
from ..state import GeometryState
from ..target import TargetName, adjacent_targets
from .candidates import generate_candidates
from .model import Candidate, SearchStep


@dataclass(frozen=True, slots=True)
class IntersectionOrigin:
    """倒数第二步新点及其全部既有支撑对象。"""

    point: Point
    supporting_drawables: tuple[Drawable, ...]


@dataclass(frozen=True, slots=True)
class TerminalDrawObligation:
    """一个最终绘制 AND 分支：两个输入点必须同时可用。"""

    candidate: Candidate
    targets: tuple[TargetName, ...]
    new_input_origins: tuple[IntersectionOrigin, ...]

    @property
    def required_points(self) -> tuple[Point, Point]:
        return (self.candidate.first, self.candidate.second)


@dataclass(frozen=True, slots=True)
class PrecursorObligationBranch:
    """根 OR 展开中的一个倒数第二步分支。"""

    candidate: Candidate
    targets: tuple[TargetName, ...]
    new_points: tuple[Point, ...]
    terminal_parameterizations_tested: int
    terminal_alternatives: tuple[TerminalDrawObligation, ...]

    @property
    def reaches_target_within_two_steps(self) -> bool:
        return bool(self.targets or self.terminal_alternatives)


@dataclass(frozen=True, slots=True)
class TwoStepObligationExpansion:
    """相对于一个有限状态的完备两步 AND/OR 义务展开。"""

    branches: tuple[PrecursorObligationBranch, ...]

    @property
    def precursor_candidates(self) -> int:
        return len(self.branches)

    @property
    def terminal_parameterizations_tested(self) -> int:
        return sum(
            branch.terminal_parameterizations_tested for branch in self.branches
        )

    @property
    def terminal_candidates(self) -> int:
        return sum(
            len(branch.terminal_alternatives) for branch in self.branches
        )

    @property
    def successful_branches(self) -> tuple[PrecursorObligationBranch, ...]:
        return tuple(
            branch
            for branch in self.branches
            if branch.reaches_target_within_two_steps
        )

    @property
    def reaches_target_within_two_steps(self) -> bool:
        return bool(self.successful_branches)


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


def generate_regular17_terminal_candidates_direct(
    state: GeometryState,
) -> tuple[Candidate, ...]:
    """直接解终步入射义务，不先物化全部非目标候选。

    枚举顺序与 :func:`generate_candidates` 相同。直线先检查三点共线式，圆先
    检查等距式；只有满足至少一个精确目标方程时才构造数学对象并做精确去重。
    """

    points = tuple(sorted(state.points))
    target_points = tuple(adjacent_targets().values())
    known_objects: list[Drawable] = list(state.drawables)
    candidates: list[Candidate] = []

    def add_if_new(candidate: Candidate) -> None:
        drawable = candidate.drawable()
        if any(
            type(existing) is type(drawable) and existing == drawable
            for existing in known_objects
        ):
            return
        known_objects.append(drawable)
        candidates.append(candidate)

    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            if any(
                _points_are_collinear(first, second, target)
                for target in target_points
            ):
                add_if_new(Candidate("line", first, second))

    for center in points:
        for through in points:
            if center == through:
                continue
            if any(
                _points_are_equidistant(center, through, target)
                for target in target_points
            ):
                add_if_new(Candidate("circle", center, through))

    return tuple(candidates)


def terminal_parameterizations_using_new_points(
    state: GeometryState,
    new_points: tuple[Point, ...],
) -> int:
    """返回至少使用一个指定新点的终步基础操作参数化数量。"""

    if not new_points:
        return 0
    if len(set(map(id, new_points))) != len(new_points):
        # ``Point`` 的 AA 坐标不承诺可哈希；先快速拦截同一对象，再做精确检查。
        raise ValueError("新点列表包含重复对象")
    if any(
        not state.contains_point(point)
        for point in new_points
    ):
        raise ValueError("指定新点不属于当前状态")
    if any(
        first == second
        for index, first in enumerate(new_points)
        for second in new_points[index + 1 :]
    ):
        raise ValueError("新点列表包含数学上相同的点")
    point_count = len(state.points)
    old_point_count = point_count - len(new_points)
    if old_point_count < 0:
        raise ValueError("新点数量超过状态点数")
    # 全部线/圆参数化减去完全由旧点定义的参数化。
    return 3 * (
        point_count * (point_count - 1)
        - old_point_count * (old_point_count - 1)
    ) // 2


def generate_regular17_terminal_candidates_using_new_points(
    state: GeometryState,
    new_points: tuple[Point, ...],
) -> tuple[Candidate, ...]:
    """精确生成至少使用一个指定新点的不同终步目标对象。

    若父状态已经完整确认不存在一步目标候选，那么加入一个首步对象后，任何合法
    两步命中的末笔都必须使用至少一个首步新交点：完全由旧点定义的末笔在父状态
    中已经可画。调用方必须先核对这一前提；本函数只实现受限终步生成。
    """

    terminal_parameterizations_using_new_points(state, new_points)
    if not new_points:
        return ()
    points = tuple(sorted(state.points))
    target_points = tuple(adjacent_targets().values())
    known_objects: list[Drawable] = list(state.drawables)
    candidates: list[Candidate] = []

    def is_new_point(point: Point) -> bool:
        return any(point == new_point for new_point in new_points)

    def add_if_new(candidate: Candidate) -> None:
        drawable = candidate.drawable()
        if any(
            type(existing) is type(drawable) and existing == drawable
            for existing in known_objects
        ):
            return
        known_objects.append(drawable)
        candidates.append(candidate)

    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            if not (is_new_point(first) or is_new_point(second)):
                continue
            if any(
                _points_are_collinear(first, second, target)
                for target in target_points
            ):
                add_if_new(Candidate("line", first, second))

    for center in points:
        for through in points:
            if center == through:
                continue
            if not (is_new_point(center) or is_new_point(through)):
                continue
            if any(
                _points_are_equidistant(center, through, target)
                for target in target_points
            ):
                add_if_new(Candidate("circle", center, through))

    return tuple(candidates)


def expand_regular17_precursor_obligation(
    state: GeometryState,
    precursor: Candidate,
) -> PrecursorObligationBranch:
    """精确展开一个倒数第二步 OR 分支的全部最终绘制选择。"""

    child, addition = _apply_precursor(state, precursor)

    precursor_targets = regular17_targets_on_step(precursor)
    if precursor_targets:
        return PrecursorObligationBranch(
            candidate=precursor,
            targets=precursor_targets,
            new_points=addition.new_points,
            terminal_parameterizations_tested=0,
            terminal_alternatives=(),
        )

    point_count = len(child.points)
    parameterizations = 3 * point_count * (point_count - 1) // 2
    terminal_alternatives = tuple(
        _build_terminal_obligation(
            state,
            child,
            addition.object,
            addition.new_points,
            terminal,
        )
        for terminal in generate_regular17_terminal_candidates_direct(child)
    )
    if any(not alternative.targets for alternative in terminal_alternatives):
        raise RuntimeError("直接终步生成器返回了不满足目标入射的候选")
    return PrecursorObligationBranch(
        candidate=precursor,
        targets=(),
        new_points=addition.new_points,
        terminal_parameterizations_tested=parameterizations,
        terminal_alternatives=terminal_alternatives,
    )


def build_regular17_two_step_obligation(
    state: GeometryState,
    precursor: Candidate,
    terminal: Candidate,
) -> TerminalDrawObligation:
    """校验并构造一条指定两步后缀的最终 AND 义务。"""

    child, addition = _apply_precursor(state, precursor)
    return _build_terminal_obligation(
        state,
        child,
        addition.object,
        addition.new_points,
        terminal,
    )


def expand_regular17_two_step_obligations(
    state: GeometryState,
) -> TwoStepObligationExpansion:
    """枚举所有合法首步，并为每步完整展开至多两步目标义务。

    根节点是 OR：任一 ``PrecursorObligationBranch`` 成功即可。每个最终绘制是
    AND：两个输入点均须可用；其中由首步产生的新输入点同时记录其全部既有
    支撑对象。候选空间不使用 shortlist、浮点阈值或超时。
    """

    return TwoStepObligationExpansion(
        branches=tuple(
            expand_regular17_precursor_obligation(state, precursor)
            for precursor in generate_candidates(state)
        )
    )


def _apply_precursor(state: GeometryState, precursor: Candidate):
    child = state.clone()
    if precursor.op == "line":
        addition = child.draw_line(precursor.first, precursor.second)
    elif precursor.op == "circle":
        addition = child.draw_circle(precursor.first, precursor.second)
    else:
        raise ValueError(f"不支持的反向义务操作 {precursor.op!r}")
    if not addition.new_object:
        raise ValueError("反向义务的倒数第二步必须产生不同的新对象")
    return child, addition


def _build_terminal_obligation(
    state: GeometryState,
    child: GeometryState,
    precursor_drawable: Drawable,
    new_points: tuple[Point, ...],
    terminal: Candidate,
) -> TerminalDrawObligation:
    for point in (terminal.first, terminal.second):
        if not child.contains_point(point):
            raise ValueError("最终绘制引用了倒数第二步后仍不可用的点")
    drawable = terminal.drawable()
    if any(
        type(existing) is type(drawable) and existing == drawable
        for existing in child.drawables
    ):
        raise ValueError("最终绘制必须产生不同的新对象")
    targets = regular17_targets_on_step(terminal)
    if not targets:
        raise ValueError("最终绘制没有满足正十七边形目标入射义务")
    return TerminalDrawObligation(
        candidate=terminal,
        targets=targets,
        new_input_origins=_new_input_origins(
            state,
            precursor_drawable,
            new_points,
            terminal,
        ),
    )


def _new_input_origins(
    state: GeometryState,
    precursor_drawable: Drawable,
    new_points: tuple[Point, ...],
    terminal: Candidate,
) -> tuple[IntersectionOrigin, ...]:
    origins: list[IntersectionOrigin] = []
    for point in (terminal.first, terminal.second):
        if not any(point == new_point for new_point in new_points):
            continue
        supporting_drawables = tuple(
            drawable for drawable in state.drawables if drawable.contains(point)
        )
        if not precursor_drawable.contains(point) or not supporting_drawables:
            raise RuntimeError("倒数第二步新输入点缺少精确交点来源")
        origins.append(
            IntersectionOrigin(
                point=point,
                supporting_drawables=supporting_drawables,
            )
        )
    return tuple(origins)


def _points_are_collinear(first: Point, second: Point, target: Point) -> bool:
    return (
        (second.x - first.x) * (target.y - first.y)
        == (second.y - first.y) * (target.x - first.x)
    )


def _points_are_equidistant(center: Point, first: Point, second: Point) -> bool:
    first_x = first.x - center.x
    first_y = first.y - center.y
    second_x = second.x - center.x
    second_y = second.y - center.y
    return (
        first_x * first_x + first_y * first_y
        == second_x * second_x + second_y * second_y
    )
