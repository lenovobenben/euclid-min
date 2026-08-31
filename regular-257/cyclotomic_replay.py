"""正 257 边形证书的精确分圆域重放器。

这里只物化证书显式绑定的交点。所有坐标均保存在 Sage
主路径保存在 ``CyclotomicField(257)`` 中；仅当平方根不属于主域时临时提升到
``UniversalCyclotomicField``。整个过程不经过浮点数或 ``AA`` 根隔离。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sage.all import CyclotomicField, UniversalCyclotomicField


FIELD = CyclotomicField(257)
ORDER_FIELD = UniversalCyclotomicField()


class ReplayError(ValueError):
    """证书程序不满足结构以外的几何语义。"""


@dataclass(frozen=True)
class Point:
    x: object
    y: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _prefer_main_field(self.x))
        object.__setattr__(self, "y", _prefer_main_field(self.y))


@dataclass(frozen=True)
class Line:
    a: object
    b: object
    c: object

    def __post_init__(self) -> None:
        a = _prefer_main_field(self.a)
        b = _prefer_main_field(self.b)
        c = _prefer_main_field(self.c)
        if a == 0 and b == 0:
            raise ReplayError("直线系数不能同时为零")
        scale = a if a != 0 else b
        object.__setattr__(self, "a", _prefer_main_field(a / scale))
        object.__setattr__(self, "b", _prefer_main_field(b / scale))
        object.__setattr__(self, "c", _prefer_main_field(c / scale))

    @classmethod
    def through(cls, first: Point, second: Point) -> "Line":
        if first == second:
            raise ReplayError("不能用同一个点画直线")
        return cls(
            first.y - second.y,
            second.x - first.x,
            first.x * second.y - second.x * first.y,
        )

    def contains(self, point: Point) -> bool:
        return self.a * point.x + self.b * point.y + self.c == 0


@dataclass(frozen=True)
class Circle:
    center: Point
    radius_squared: object

    def __post_init__(self) -> None:
        radius_squared = _prefer_main_field(self.radius_squared)
        if radius_squared <= 0:
            raise ReplayError("圆的半径平方必须为正")
        object.__setattr__(self, "radius_squared", radius_squared)

    @classmethod
    def through(cls, center: Point, through: Point) -> "Circle":
        if center == through:
            raise ReplayError("圆心和圆上点不能重合")
        return cls(center, squared_distance(center, through))

    def contains(self, point: Point) -> bool:
        return squared_distance(self.center, point) == self.radius_squared


Drawable = Line | Circle
NamedObject = Point | Drawable


def squared_distance(first: Point, second: Point):
    dx = first.x - second.x
    dy = first.y - second.y
    return dx * dx + dy * dy


def intersection_points(first: Drawable, second: Drawable) -> tuple[Point, ...]:
    """返回按 x、再按 y 精确升序排列的不同有限实交点。"""

    if isinstance(first, Line) and isinstance(second, Line):
        points = _line_line(first, second)
    elif isinstance(first, Line) and isinstance(second, Circle):
        points = _line_circle(first, second)
    elif isinstance(first, Circle) and isinstance(second, Line):
        points = _line_circle(second, first)
    elif isinstance(first, Circle) and isinstance(second, Circle):
        points = _circle_circle(first, second)
    else:
        raise TypeError("求交只支持直线和圆")
    return tuple(_sorted_unique(points))


def _line_line(first: Line, second: Line) -> tuple[Point, ...]:
    determinant = first.a * second.b - second.a * first.b
    if determinant == 0:
        return ()
    return (
        Point(
            (first.b * second.c - second.b * first.c) / determinant,
            (first.c * second.a - second.c * first.a) / determinant,
        ),
    )


def _line_circle(line: Line, circle: Circle) -> tuple[Point, ...]:
    norm_squared = line.a * line.a + line.b * line.b
    signed = (
        line.a * circle.center.x
        + line.b * circle.center.y
        + line.c
    )
    foot = Point(
        circle.center.x - line.a * signed / norm_squared,
        circle.center.y - line.b * signed / norm_squared,
    )
    remaining_squared = (
        circle.radius_squared - signed * signed / norm_squared
    )
    if remaining_squared < 0:
        return ()
    if remaining_squared == 0:
        return (foot,)

    scale = _sqrt_exact(remaining_squared / norm_squared)
    return (
        Point(foot.x - line.b * scale, foot.y + line.a * scale),
        Point(foot.x + line.b * scale, foot.y - line.a * scale),
    )


def _circle_circle(first: Circle, second: Circle) -> tuple[Point, ...]:
    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    if dx == 0 and dy == 0:
        return ()
    radical_axis = Line(
        2 * dx,
        2 * dy,
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius_squared
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius_squared,
    )
    return _line_circle(radical_axis, first)


def _sorted_unique(points: tuple[Point, ...]) -> list[Point]:
    ordered = sorted(
        points,
        key=lambda point: (
            _order_value(point.x),
            _order_value(point.y),
        ),
    )
    unique: list[Point] = []
    for point in ordered:
        if not unique or point != unique[-1]:
            unique.append(point)
    return unique


def _prefer_main_field(value):
    """能精确降到 Q(zeta_257) 时立即降域，否则保留原精确父环。"""

    if hasattr(value, "parent") and value.parent() is ORDER_FIELD:
        return value
    try:
        return FIELD(value)
    except (TypeError, ValueError):
        return value


def _sqrt_exact(value):
    """优先在主域开方；非主域平方根提升到通用分圆域。"""

    root = value.sqrt()
    if root.parent() is FIELD:
        return root
    return ORDER_FIELD(value).sqrt()


def _order_value(value):
    """把实分圆元素提升到具有精确实序的通用分圆域。"""

    try:
        return ORDER_FIELD(value)
    except (TypeError, ValueError) as error:
        raise ReplayError("交点坐标不能嵌入精确有序分圆域") from error


@dataclass(frozen=True)
class ReplayResult:
    names: dict[str, NamedObject]
    lines: tuple[Line, ...]
    circles: tuple[Circle, ...]
    line_draws: int
    circle_draws: int
    bound_point_e_moves: dict[str, int]

    @property
    def e_move(self) -> int:
        return self.line_draws + self.circle_draws


class CyclotomicReplayer:
    """顺序执行 257 专用证书程序并核对所有显式交点分支。"""

    def __init__(self) -> None:
        center = Point(0, -1)
        initial = Point(0, 1)
        target_circle = Circle.through(center, initial)
        self.names: dict[str, NamedObject] = {
            "C": center,
            "B": initial,
            "c0": target_circle,
        }
        self.lines: list[Line] = []
        self.circles: list[Circle] = [target_circle]
        self.line_draws = 0
        self.circle_draws = 0
        self.bound_point_e_moves = {"C": 0, "B": 0}
        self._intersection_cache: dict[tuple[str, str], tuple[Point, ...]] = {}

    @property
    def e_move(self) -> int:
        return self.line_draws + self.circle_draws

    def replay(self, program: list[dict[str, Any]]) -> ReplayResult:
        for program_index, entry in enumerate(program):
            try:
                self.execute(entry)
            except Exception as error:
                if isinstance(error, ReplayError):
                    raise ReplayError(
                        f"program[{program_index}] {entry.get('id')!r}: {error}"
                    ) from error
                raise
        return self.result()

    def execute(self, entry: dict[str, Any]) -> None:
        entry_id = entry["id"]
        if entry_id in self.names:
            raise ReplayError(f"ID {entry_id!r} 重复声明")
        operation = entry["op"]
        if operation == "line":
            first, second = map(self._point, entry["through"])
            line = Line.through(first, second)
            self.line_draws += 1
            self.lines.append(line)
            self.names[entry_id] = line
            return
        if operation == "circle":
            circle = Circle.through(
                self._point(entry["center"]),
                self._point(entry["through"]),
            )
            self.circle_draws += 1
            self.circles.append(circle)
            self.names[entry_id] = circle
            return
        if operation == "intersect":
            first_reference, second_reference = entry["objects"]
            points = self.points_for(first_reference, second_reference)
            index = entry["index"]
            if index >= len(points):
                raise ReplayError(
                    f"交点索引 {index} 越界；实际只有 {len(points)} 个交点"
                )
            point = points[index]
            self.names[entry_id] = point
            self.bound_point_e_moves[entry_id] = self.e_move
            return
        raise ReplayError(f"不支持操作 {operation!r}")

    def points_for(self, first_reference: str, second_reference: str):
        key = tuple(sorted((first_reference, second_reference)))
        if key not in self._intersection_cache:
            self._intersection_cache[key] = intersection_points(
                self._drawable(first_reference),
                self._drawable(second_reference),
            )
        return self._intersection_cache[key]

    def index_for_witness(
        self,
        first_reference: str,
        second_reference: str,
        witness: Point,
    ) -> int:
        """用已给精确交点作为 proof hint，验证关联并求字典序索引。"""

        first = self._drawable(first_reference)
        second = self._drawable(second_reference)
        if isinstance(first, Line) and isinstance(second, Line):
            determinant = first.a * second.b - second.a * first.b
            if (
                determinant == 0
                or not first.contains(witness)
                or not second.contains(witness)
            ):
                raise ReplayError("proof hint 不是两条非平行直线的交点")
            return 0
        if isinstance(first, Line) and isinstance(second, Circle):
            return _line_circle_witness_index(first, second, witness)
        if isinstance(first, Circle) and isinstance(second, Line):
            return _line_circle_witness_index(second, first, witness)
        if isinstance(first, Circle) and isinstance(second, Circle):
            if not first.contains(witness) or not second.contains(witness):
                raise ReplayError("proof hint 不在两个圆上")
            dx = second.center.x - first.center.x
            dy = second.center.y - first.center.y
            if dx == 0 and dy == 0:
                raise ReplayError("同心圆不能用孤立交点 proof hint")
            radical_axis = Line(
                2 * dx,
                2 * dy,
                first.center.x * first.center.x
                + first.center.y * first.center.y
                - first.radius_squared
                - second.center.x * second.center.x
                - second.center.y * second.center.y
                + second.radius_squared,
            )
            return _line_circle_witness_index(radical_axis, first, witness)
        raise TypeError("求交只支持直线和圆")

    def bind_witness(
        self,
        entry: dict[str, Any],
        witness: Point,
        *,
        verified_index: int | None = None,
    ) -> None:
        """验证证书索引与 proof hint 一致后绑定该精确点。"""

        entry_id = entry["id"]
        if entry_id in self.names:
            raise ReplayError(f"ID {entry_id!r} 重复声明")
        if entry.get("op") != "intersect":
            raise ReplayError("proof hint 只适用于 intersect 条目")
        first, second = entry["objects"]
        actual_index = (
            verified_index
            if verified_index is not None
            else self.index_for_witness(first, second, witness)
        )
        if entry["index"] != actual_index:
            raise ReplayError(
                f"声明索引 {entry['index']} 与精确字典序 {actual_index} 不一致"
            )
        self.names[entry_id] = witness
        self.bound_point_e_moves[entry_id] = self.e_move

    def result(self) -> ReplayResult:
        return ReplayResult(
            names=dict(self.names),
            lines=tuple(self.lines),
            circles=tuple(self.circles),
            line_draws=self.line_draws,
            circle_draws=self.circle_draws,
            bound_point_e_moves=dict(self.bound_point_e_moves),
        )

    def _point(self, reference: str) -> Point:
        value = self._reference(reference)
        if not isinstance(value, Point):
            raise ReplayError(f"引用 {reference!r} 不是点")
        return value

    def _drawable(self, reference: str) -> Drawable:
        value = self._reference(reference)
        if not isinstance(value, (Line, Circle)):
            raise ReplayError(f"引用 {reference!r} 不是直线或圆")
        return value

    def _reference(self, reference: str) -> NamedObject:
        try:
            return self.names[reference]
        except KeyError as error:
            raise ReplayError(f"引用 {reference!r} 尚未声明") from error


def _line_circle_witness_index(
    line: Line,
    circle: Circle,
    witness: Point,
) -> int:
    if not line.contains(witness) or not circle.contains(witness):
        raise ReplayError("proof hint 不是直线与圆的交点")
    norm_squared = line.a * line.a + line.b * line.b
    signed = (
        line.a * circle.center.x
        + line.b * circle.center.y
        + line.c
    )
    foot = Point(
        circle.center.x - line.a * signed / norm_squared,
        circle.center.y - line.b * signed / norm_squared,
    )
    other = Point(2 * foot.x - witness.x, 2 * foot.y - witness.y)
    points = _sorted_unique((witness, other))
    for index, point in enumerate(points):
        if point == witness:
            return index
    raise AssertionError("proof hint 在反射交点列表中丢失")
