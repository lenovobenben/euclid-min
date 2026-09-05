"""构造程序的确定性名称环境、重放和 E-move 计分。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import VerificationError
from .geometry import (
    Circle,
    CoincidentPointsError,
    Drawable,
    Line,
    Point,
)
from .intersections import IntersectionKind, intersect
from .state import ImplicitClosureState
from .target import TargetName, reached_targets_by_object_pair


NamedObject = Point | Drawable


@dataclass(frozen=True, slots=True)
class ReplayResult:
    state: ImplicitClosureState
    names: dict[str, NamedObject]
    line_draws: int
    circle_draws: int
    duplicate_draws: int
    targets: tuple[TargetName, ...]
    first_target_program_index: int | None
    first_target_e_move: int | None

    @property
    def e_move(self) -> int:
        return self.line_draws + self.circle_draws


class ProgramReplayer:
    """按 `euclid-min-certificate/v1` 顺序执行 program。"""

    def __init__(self) -> None:
        self.state = ImplicitClosureState.fixed_initial()
        origin, start = self.state.points
        unit_circle = self.state.circles[0]
        self.names: dict[str, NamedObject] = {
            "O": origin,
            "A": start,
            "unit_circle": unit_circle,
        }
        self.line_draws = 0
        self.circle_draws = 0
        self.duplicate_draws = 0
        self.first_target_program_index: int | None = None
        self.first_target_e_move: int | None = None
        self._targets: set[TargetName] = set()

    def replay(self, program: list[dict[str, Any]]) -> ReplayResult:
        for program_index, entry in enumerate(program):
            entry_id = entry.get("id")
            try:
                self._execute(entry, program_index)
            except VerificationError as error:
                if error.program_index is None:
                    error.program_index = program_index
                if error.entry_id is None and isinstance(entry_id, str):
                    error.entry_id = entry_id
                error.details.setdefault(
                    "consumed_e_moves_before_error", self.e_move
                )
                raise

        targets = tuple(
            target
            for target in (TargetName.B_PLUS, TargetName.B_MINUS)
            if target in self._targets
        )
        return ReplayResult(
            state=self.state,
            names=dict(self.names),
            line_draws=self.line_draws,
            circle_draws=self.circle_draws,
            duplicate_draws=self.duplicate_draws,
            targets=targets,
            first_target_program_index=self.first_target_program_index,
            first_target_e_move=self.first_target_e_move,
        )

    @property
    def e_move(self) -> int:
        return self.line_draws + self.circle_draws

    def _execute(self, entry: dict[str, Any], program_index: int) -> None:
        entry_id = entry.get("id")
        if not isinstance(entry_id, str):
            raise VerificationError("schema_invalid", "程序条目缺少有效 id")
        if entry_id in self.names:
            raise VerificationError(
                "duplicate_id",
                f"ID {entry_id!r} 已经声明",
            )

        operation = entry.get("op")
        if operation == "line":
            self._draw_line(entry_id, entry["through"], program_index)
        elif operation == "circle":
            self._draw_circle(
                entry_id,
                entry["center"],
                entry["through"],
                program_index,
            )
        elif operation == "intersect":
            self._bind_intersection(
                entry_id,
                entry["objects"],
                entry["index"],
            )
        else:
            raise VerificationError(
                "unsupported_operation",
                f"不支持操作 {operation!r}",
            )

        # Keep the exact AA values but reduce their internal representations.
        # This prevents equivalent nested-radical expressions from making a
        # later exact equality check needlessly expensive.
        self._simplify_named_value(self.names[entry_id])

    @staticmethod
    def _simplify_named_value(value: NamedObject) -> None:
        if isinstance(value, Point):
            coordinates = (value.x, value.y)
        elif isinstance(value, Line):
            coordinates = (value.a, value.b, value.c)
        else:
            coordinates = (
                value.center.x,
                value.center.y,
                value.radius_squared,
            )
        for coordinate in coordinates:
            coordinate.simplify()

    def _draw_line(
        self,
        entry_id: str,
        references: list[str],
        program_index: int,
    ) -> None:
        first = self._point_reference(references[0])
        second = self._point_reference(references[1])
        try:
            addition = self.state.draw_line(first, second)
        except CoincidentPointsError as error:
            raise VerificationError(
                "coincident_input_points", str(error)
            ) from error

        self.line_draws += 1
        if not addition.new_object:
            self.duplicate_draws += 1
        self.names[entry_id] = addition.object
        if addition.new_object:
            self._record_object_targets(addition.object, program_index)

    def _draw_circle(
        self,
        entry_id: str,
        center_reference: str,
        through_reference: str,
        program_index: int,
    ) -> None:
        center = self._point_reference(center_reference)
        through = self._point_reference(through_reference)
        try:
            addition = self.state.draw_circle(center, through)
        except CoincidentPointsError as error:
            raise VerificationError(
                "coincident_input_points", str(error)
            ) from error

        self.circle_draws += 1
        if not addition.new_object:
            self.duplicate_draws += 1
        self.names[entry_id] = addition.object
        if addition.new_object:
            self._record_object_targets(addition.object, program_index)

    def _bind_intersection(
        self,
        entry_id: str,
        references: list[str],
        index: int,
    ) -> None:
        first = self._drawable_reference(references[0])
        second = self._drawable_reference(references[1])
        result = intersect(first, second)
        if result.kind == IntersectionKind.COINCIDENT:
            raise VerificationError(
                "coincident_intersection_objects",
                "重合对象没有可按索引选择的孤立交点",
            )
        if index >= len(result.points):
            raise VerificationError(
                "intersection_index_out_of_range",
                f"交点索引 {index} 超出范围；对象对只有 {len(result.points)} 个有限实交点",
                details={"intersection_count": len(result.points)},
            )

        point = self.state.bind_point(result.points[index])
        self.names[entry_id] = point

    def _point_reference(self, reference: str) -> Point:
        value = self._reference(reference)
        if not isinstance(value, Point):
            raise VerificationError(
                "wrong_reference_type",
                f"引用 {reference!r} 必须指向 point",
                details={"reference": reference, "expected_type": "point"},
            )
        return value

    def _drawable_reference(self, reference: str) -> Drawable:
        value = self._reference(reference)
        if not isinstance(value, (Line, Circle)):
            raise VerificationError(
                "wrong_reference_type",
                f"引用 {reference!r} 必须指向 line 或 circle",
                details={
                    "reference": reference,
                    "expected_type": "line_or_circle",
                },
            )
        return value

    def _reference(self, reference: str) -> NamedObject:
        try:
            return self.names[reference]
        except KeyError as error:
            raise VerificationError(
                "unknown_reference",
                f"引用 {reference!r} 尚未声明",
                details={"reference": reference},
            ) from error

    def _record_object_targets(
        self,
        new_object: Drawable,
        program_index: int,
    ) -> None:
        newly_reached: set[TargetName] = set()
        for other in self.state.drawables:
            if other is new_object:
                continue
            newly_reached.update(
                reached_targets_by_object_pair(new_object, other)
            )
        if not newly_reached:
            return
        self._targets.update(newly_reached)
        if self.first_target_program_index is None:
            self.first_target_program_index = program_index
            self.first_target_e_move = self.e_move
