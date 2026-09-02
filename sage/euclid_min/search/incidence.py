"""目标入射的严格区间判定；未决项显式保留，不触发昂贵数域合并。"""

from __future__ import annotations

from dataclasses import dataclass

from sage.all import RealIntervalField

from ..geometry import Drawable, Point
from ..state import GeometryState
from ..target import adjacent_targets
from .model import Candidate


STRICT_INTERVAL_FIELD = RealIntervalField(128)


@dataclass(slots=True)
class IncidenceAudit:
    """严格区间与最终精确回退的逐类计数。"""

    tested_parameterizations: int = 0
    fast_interval_nonzero: int = 0
    refined_interval_nonzero: int = 0
    exact_fallbacks: int = 0
    exact_zeros: int = 0
    structural_existing_objects: int = 0
    deferred_relations: int = 0

    def add(self, other: "IncidenceAudit") -> None:
        self.tested_parameterizations += other.tested_parameterizations
        self.fast_interval_nonzero += other.fast_interval_nonzero
        self.refined_interval_nonzero += other.refined_interval_nonzero
        self.exact_fallbacks += other.exact_fallbacks
        self.exact_zeros += other.exact_zeros
        self.structural_existing_objects += other.structural_existing_objects
        self.deferred_relations += other.deferred_relations

    def as_dict(self) -> dict:
        return {
            "tested_parameterizations": self.tested_parameterizations,
            "fast_interval_nonzero": self.fast_interval_nonzero,
            "refined_interval_nonzero": self.refined_interval_nonzero,
            "exact_fallbacks": self.exact_fallbacks,
            "exact_zeros": self.exact_zeros,
            "structural_existing_objects": self.structural_existing_objects,
            "deferred_relations": self.deferred_relations,
        }


@dataclass(frozen=True, slots=True)
class DeferredIncidence:
    """区间无法判定的一个目标入射等式；不携带不可移植 AA 坐标。"""

    operation: str
    first_point_index: int
    second_point_index: int
    target: str

    def as_dict(self) -> dict:
        return {
            "operation": self.operation,
            "first_point_index": self.first_point_index,
            "second_point_index": self.second_point_index,
            "target": self.target,
        }


@dataclass(frozen=True, slots=True)
class DeferredIncidenceGeneration:
    candidates: tuple[Candidate, ...]
    deferred: tuple[DeferredIncidence, ...]
    audit: IncidenceAudit


def _certified_zero(value, audit: IncidenceAudit) -> bool:
    """严格判断零；区间排除是证明，区间未决才调用 AA 等号。"""

    fast = value.interval_fast(STRICT_INTERVAL_FIELD)
    if 0 not in fast:
        audit.fast_interval_nonzero += 1
        return False
    refined = value.interval(STRICT_INTERVAL_FIELD)
    if 0 not in refined:
        audit.refined_interval_nonzero += 1
        return False
    audit.exact_fallbacks += 1
    result = value == 0
    audit.exact_zeros += int(result)
    return result


def _interval_zero_or_defer(value, audit: IncidenceAudit) -> bool | None:
    """用逐级严格实区间返回零、非零或未决，不调用 ``AA == 0``。"""

    for precision in (128, 256, 512, 1024):
        field = RealIntervalField(precision)
        interval = (
            value.interval_fast(field)
            if precision == 128
            else value.interval(field)
        )
        if 0 not in interval:
            if precision == 128:
                audit.fast_interval_nonzero += 1
            else:
                audit.refined_interval_nonzero += 1
            return False
        if interval.lower() == 0 and interval.upper() == 0:
            audit.exact_zeros += 1
            return True
    audit.deferred_relations += 1
    return None


def _collinearity_residual(first: Point, second: Point, target: Point):
    return (
        (second.x - first.x) * (target.y - first.y)
        - (second.y - first.y) * (target.x - first.x)
    )


def _equidistance_residual(center: Point, through: Point, target: Point):
    through_x = through.x - center.x
    through_y = through.y - center.y
    target_x = target.x - center.x
    target_y = target.y - center.y
    return (
        through_x * through_x
        + through_y * through_y
        - target_x * target_x
        - target_y * target_y
    )


def generate_terminal_candidates_using_new_points_strict(
    state: GeometryState,
    new_points: tuple[Point, ...],
) -> tuple[tuple[Candidate, ...], IncidenceAudit]:
    """生成至少使用一个新点的目标对象，并审计每次严格判定。

    浮点数不参与接受或排除。``interval_fast`` 和 ``interval`` 返回包含真实值的
    Sage 实区间；只有区间严格不含零时才排除。仍包含零的极少数表达式继续使用
    原有 ``AA == 0``，所以该预筛不会产生假阴性。
    """

    if not new_points:
        return (), IncidenceAudit()
    if any(not state.contains_point(point) for point in new_points):
        raise ValueError("指定新点不属于当前状态")
    if any(
        first == second
        for index, first in enumerate(new_points)
        for second in new_points[index + 1 :]
    ):
        raise ValueError("新点列表包含数学上相同的点")

    points = tuple(sorted(state.points))
    target_points = tuple(adjacent_targets().values())
    known_objects: list[Drawable] = list(state.drawables)
    candidates: list[Candidate] = []
    audit = IncidenceAudit()

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
            audit.tested_parameterizations += 1
            if any(
                _certified_zero(
                    _collinearity_residual(first, second, target), audit
                )
                for target in target_points
            ):
                add_if_new(Candidate("line", first, second))

    for center in points:
        for through in points:
            if center == through:
                continue
            if not (is_new_point(center) or is_new_point(through)):
                continue
            audit.tested_parameterizations += 1
            if any(
                _certified_zero(
                    _equidistance_residual(center, through, target), audit
                )
                for target in target_points
            ):
                add_if_new(Candidate("circle", center, through))

    return tuple(candidates), audit


def new_points_on_existing_drawable(
    parent_state: GeometryState,
    addition,
    drawable: Drawable,
) -> tuple[Point, ...]:
    """从求交结果 provenance 读取首步与指定既有对象产生的新点。"""

    try:
        drawable_index = next(
            index
            for index, existing in enumerate(parent_state.drawables)
            if existing is drawable
        )
    except StopIteration as error:
        raise ValueError("指定对象不属于首步之前的状态") from error
    if len(addition.intersections) != len(parent_state.drawables):
        raise ValueError("首步求交结果与父状态对象数不一致")
    result_points = addition.intersections[drawable_index].points
    return tuple(
        point
        for point in addition.new_points
        if any(point is result_point for result_point in result_points)
    )


def generate_terminal_candidates_with_deferred_incidence(
    state: GeometryState,
    new_points: tuple[Point, ...],
    *,
    new_unit_circle_points: tuple[Point, ...] = (),
) -> DeferredIncidenceGeneration:
    """严格区间排除非零项，把未决关系落盘而不触发 QQbar 数域合并。

    当前父状态尚未命中目标，因此已有对象中唯一经过目标的是单位圆本身。若末步
    以 ``O`` 为圆心并经过首步与单位圆产生的新点，它只是重复单位圆，可以直接按
    provenance 排除，无需证明一个高次数 AA 等距式等于零。
    """

    if not new_points:
        return DeferredIncidenceGeneration((), (), IncidenceAudit())
    if any(not state.contains_point(point) for point in new_points):
        raise ValueError("指定新点不属于当前状态")
    points = tuple(sorted(state.points))
    targets = tuple(adjacent_targets().items())
    known_objects: list[Drawable] = list(state.drawables)
    unit_circle = state.circles[0]
    candidates: list[Candidate] = []
    deferred: list[DeferredIncidence] = []
    audit = IncidenceAudit()

    def is_new_point(point: Point) -> bool:
        return any(point is new_point for new_point in new_points)

    def add_if_new(candidate: Candidate) -> None:
        drawable = candidate.drawable()
        if any(
            type(existing) is type(drawable) and existing == drawable
            for existing in known_objects
        ):
            return
        known_objects.append(drawable)
        candidates.append(candidate)

    def classify(
        operation: str,
        first_index: int,
        second_index: int,
        residual_builder,
    ) -> bool:
        for target_name, target in targets:
            status = _interval_zero_or_defer(residual_builder(target), audit)
            if status is True:
                return True
            if status is None:
                deferred.append(
                    DeferredIncidence(
                        operation,
                        first_index,
                        second_index,
                        target_name.value,
                    )
                )
        return False

    for first_index, first in enumerate(points):
        for second_index in range(first_index + 1, len(points)):
            second = points[second_index]
            if not (is_new_point(first) or is_new_point(second)):
                continue
            audit.tested_parameterizations += 1
            if classify(
                "line",
                first_index,
                second_index,
                lambda target: _collinearity_residual(first, second, target),
            ):
                add_if_new(Candidate("line", first, second))

    for first_index, center in enumerate(points):
        for second_index, through in enumerate(points):
            if center is through:
                continue
            if not (is_new_point(center) or is_new_point(through)):
                continue
            audit.tested_parameterizations += 1
            if center is unit_circle.center and any(
                through is point for point in new_unit_circle_points
            ):
                audit.structural_existing_objects += 1
                continue
            if classify(
                "circle",
                first_index,
                second_index,
                lambda target: _equidistance_residual(center, through, target),
            ):
                add_if_new(Candidate("circle", center, through))

    return DeferredIncidenceGeneration(
        tuple(candidates),
        tuple(deferred),
        audit,
    )
