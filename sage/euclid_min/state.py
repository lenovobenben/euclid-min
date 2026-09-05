"""去重后的精确几何状态和自动交点闭包。"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Circle, Drawable, Line, Point
from .intersections import IntersectionResult, intersect


_COMPLEXITY_CAP = 1_000_000_000


class PointNotInStateError(ValueError):
    """基础操作引用了尚未位于数学状态中的点。"""


@dataclass(frozen=True, slots=True)
class AdditionResult:
    """向状态加入一个 drawable 后的确定性结果。"""

    object: Drawable
    new_object: bool
    new_points: tuple[Point, ...]
    intersections: tuple[IntersectionResult, ...]


class GeometryState:
    """参考实现使用线性精确比较的状态容器。

    M1 首先保证正确性；未来可以增加 hash 索引，但 hash 命中后仍须精确确认。
    """

    def __init__(self) -> None:
        self._points: list[Point] = []
        self._point_levels: list[int] = []
        self._point_complexities: list[int] = []
        self._lines: list[Line] = []
        self._line_levels: list[int] = []
        self._line_complexities: list[int] = []
        self._circles: list[Circle] = []
        self._circle_levels: list[int] = []
        self._circle_complexities: list[int] = []

    @classmethod
    def fixed_initial(cls) -> "GeometryState":
        """创建 `regular-17-e-fixed-v1` 的免费初始状态。"""

        state = cls()
        origin = Point(0, 0)
        start = Point(1, 0)
        state._add_point(origin, level=0, complexity=1)
        state._add_point(start, level=0, complexity=1)
        state.add_circle(
            Circle.through(origin, start),
            level=0,
            complexity=1,
        )
        return state

    @property
    def points(self) -> tuple[Point, ...]:
        return tuple(self._points)

    @property
    def point_levels(self) -> tuple[int, ...]:
        """与 ``points`` 对齐的启发式生成层级；不参与数学状态相等。"""

        return tuple(self._point_levels)

    @property
    def point_complexities(self) -> tuple[int, ...]:
        """与 ``points`` 对齐的廉价 provenance 复杂度代理。"""

        return tuple(self._point_complexities)

    @property
    def lines(self) -> tuple[Line, ...]:
        return tuple(self._lines)

    @property
    def circles(self) -> tuple[Circle, ...]:
        return tuple(self._circles)

    @property
    def drawables(self) -> tuple[Drawable, ...]:
        return (*self._lines, *self._circles)

    def clone(self) -> "GeometryState":
        """复制数学状态；AA 和几何值对象均不可变，可以安全共享。"""

        clone = type(self)()
        clone._points = list(self._points)
        clone._point_levels = list(self._point_levels)
        clone._point_complexities = list(self._point_complexities)
        clone._lines = list(self._lines)
        clone._line_levels = list(self._line_levels)
        clone._line_complexities = list(self._line_complexities)
        clone._circles = list(self._circles)
        clone._circle_levels = list(self._circle_levels)
        clone._circle_complexities = list(self._circle_complexities)
        return clone

    def point_level(self, point: Point) -> int:
        """返回点首次可由当前路径生成的依赖层级。"""

        index = self._find_equal_index(self._points, point)
        if index is None:
            raise PointNotInStateError("点不在当前数学状态中")
        return self._point_levels[index]

    def point_complexity(self, point: Point) -> int:
        """返回点的 provenance 复杂度代理；不计算最小多项式。"""

        index = self._find_equal_index(self._points, point)
        if index is None:
            raise PointNotInStateError("点不在当前数学状态中")
        return self._point_complexities[index]

    def contains_point(self, point: Point) -> bool:
        return self._find_equal(self._points, point) is not None

    def contains_line(self, line: Line) -> bool:
        return self._find_equal(self._lines, line) is not None

    def contains_circle(self, circle: Circle) -> bool:
        return self._find_equal(self._circles, circle) is not None

    def draw_line(self, first: Point, second: Point) -> AdditionResult:
        """用状态中的两个点画线并执行自动交点闭包。"""

        self._require_points(first, second)
        level = 1 + max(self.point_level(first), self.point_level(second))
        complexity = _bounded_product(
            self.point_complexity(first),
            self.point_complexity(second),
        )
        return self.add_line(
            Line.through(first, second),
            level=level,
            complexity=complexity,
        )

    def draw_circle(self, center: Point, through: Point) -> AdditionResult:
        """用状态中的两个点画基础圆并执行自动交点闭包。"""

        self._require_points(center, through)
        level = 1 + max(self.point_level(center), self.point_level(through))
        complexity = _bounded_product(
            self.point_complexity(center),
            self.point_complexity(through),
            factor=2,
        )
        return self.add_circle(
            Circle.through(center, through),
            level=level,
            complexity=complexity,
        )

    def add_line(
        self,
        line: Line,
        *,
        level: int = 0,
        complexity: int = 1,
    ) -> AdditionResult:
        """加入精确直线；重复对象不重新求交。"""

        existing = self._find_equal(self._lines, line)
        if existing is not None:
            return AdditionResult(existing, False, (), ())

        results = [
            (
                intersect(line, old),
                max(level, old_level),
                _bounded_product(complexity, old_complexity),
            )
            for old, old_level, old_complexity in zip(
                self._lines,
                self._line_levels,
                self._line_complexities,
            )
        ]
        results.extend(
            (
                intersect(line, old),
                max(level, old_level),
                _bounded_product(complexity, old_complexity, factor=2),
            )
            for old, old_level, old_complexity in zip(
                self._circles,
                self._circle_levels,
                self._circle_complexities,
            )
        )
        self._lines.append(line)
        self._line_levels.append(level)
        self._line_complexities.append(complexity)
        new_points = self._add_intersection_points(results)
        return AdditionResult(
            line,
            True,
            new_points,
            tuple(result for result, _point_level, _complexity in results),
        )

    def add_circle(
        self,
        circle: Circle,
        *,
        level: int = 0,
        complexity: int = 1,
    ) -> AdditionResult:
        """加入精确圆；重复对象不重新求交。"""

        existing = self._find_equal(self._circles, circle)
        if existing is not None:
            return AdditionResult(existing, False, (), ())

        results = [
            (
                intersect(circle, old),
                max(level, old_level),
                _bounded_product(complexity, old_complexity, factor=2),
            )
            for old, old_level, old_complexity in zip(
                self._lines,
                self._line_levels,
                self._line_complexities,
            )
        ]
        results.extend(
            (
                intersect(circle, old),
                max(level, old_level),
                _bounded_product(complexity, old_complexity, factor=2),
            )
            for old, old_level, old_complexity in zip(
                self._circles,
                self._circle_levels,
                self._circle_complexities,
            )
        )
        self._circles.append(circle)
        self._circle_levels.append(level)
        self._circle_complexities.append(complexity)
        new_points = self._add_intersection_points(results)
        return AdditionResult(
            circle,
            True,
            new_points,
            tuple(result for result, _point_level, _complexity in results),
        )

    def _add_intersection_points(
        self, results: list[tuple[IntersectionResult, int, int]]
    ) -> tuple[Point, ...]:
        new_points: list[Point] = []
        for result, level, complexity in results:
            for point in result.points:
                if self._add_point(
                    point,
                    level=level,
                    complexity=complexity,
                ):
                    new_points.append(point)
        return tuple(new_points)

    def _add_point(
        self,
        point: Point,
        *,
        level: int = 0,
        complexity: int = 1,
    ) -> bool:
        existing_index = self._find_equal_index(self._points, point)
        if existing_index is not None:
            self._point_levels[existing_index] = min(
                self._point_levels[existing_index],
                level,
            )
            self._point_complexities[existing_index] = min(
                self._point_complexities[existing_index],
                complexity,
            )
            return False
        self._points.append(point)
        self._point_levels.append(level)
        self._point_complexities.append(complexity)
        return True

    def _require_points(self, *points: Point) -> None:
        for point in points:
            if not self.contains_point(point):
                raise PointNotInStateError("基础操作只能使用当前状态中的点")

    @staticmethod
    def _find_equal(items, candidate):
        # AA equality cost depends on the representation being compared.  A
        # normalized line often has a cheap constant term even when its
        # leading coefficient carries a deeply nested radical expression.
        # Compare the cheap fields first without changing exact semantics.
        if isinstance(candidate, Line):
            for item in items:
                if (
                    item.c == candidate.c
                    and item.b == candidate.b
                    and item.a == candidate.a
                ):
                    return item
            return None
        for item in items:
            if item == candidate:
                return item
        return None

    @staticmethod
    def _find_equal_index(items, candidate) -> int | None:
        for index, item in enumerate(items):
            if item == candidate:
                return index
        return None


def _bounded_product(first: int, second: int, *, factor: int = 1) -> int:
    """返回有上限的廉价 provenance 乘积，避免路径增长造成大整数热点。"""

    return min(_COMPLEXITY_CAP, factor * max(1, first) * max(1, second))


class ImplicitClosureState:
    """验证器使用的惰性交点闭包状态。

    数学状态仍包含每一对已构造对象的全部有限实交点，但这里只物化证书通过
    ``intersect`` 绑定了名称的点。这样不会为了验证一条构造路径而提前生成
    永远不会被引用的高次数代数数。完整的显式闭包参考实现仍由
    :class:`GeometryState` 提供。
    """

    def __init__(self) -> None:
        self._points: list[Point] = []
        self._lines: list[Line] = []
        self._circles: list[Circle] = []

    @classmethod
    def fixed_initial(cls) -> "ImplicitClosureState":
        state = cls()
        origin = Point(0, 0)
        start = Point(1, 0)
        state._points.extend((origin, start))
        state._circles.append(Circle.through(origin, start))
        return state

    @property
    def points(self) -> tuple[Point, ...]:
        """返回已经显式绑定的不同点；未绑定交点仍隐式存在。"""

        return tuple(self._points)

    @property
    def lines(self) -> tuple[Line, ...]:
        return tuple(self._lines)

    @property
    def circles(self) -> tuple[Circle, ...]:
        return tuple(self._circles)

    @property
    def drawables(self) -> tuple[Drawable, ...]:
        return (*self._lines, *self._circles)

    def bind_point(self, point: Point) -> Point:
        """物化一个已经由两个已构造对象确定的交点。"""

        existing = GeometryState._find_equal(self._points, point)
        if existing is not None:
            return existing
        self._points.append(point)
        return point

    def draw_line(self, first: Point, second: Point) -> AdditionResult:
        self._require_points(first, second)
        line = Line.through(first, second)
        existing = GeometryState._find_equal(self._lines, line)
        if existing is not None:
            return AdditionResult(existing, False, (), ())
        self._lines.append(line)
        return AdditionResult(line, True, (), ())

    def draw_circle(self, center: Point, through: Point) -> AdditionResult:
        self._require_points(center, through)
        circle = Circle.through(center, through)
        existing = GeometryState._find_equal(self._circles, circle)
        if existing is not None:
            return AdditionResult(existing, False, (), ())
        self._circles.append(circle)
        return AdditionResult(circle, True, (), ())

    def _require_points(self, *points: Point) -> None:
        for point in points:
            if GeometryState._find_equal(self._points, point) is None:
                raise PointNotInStateError(
                    "基础操作只能使用已经显式绑定名称的点"
                )
