"""去重后的精确几何状态和自动交点闭包。"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Circle, Drawable, Line, Point
from .intersections import IntersectionResult, intersect


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
        self._lines: list[Line] = []
        self._circles: list[Circle] = []

    @classmethod
    def fixed_initial(cls) -> "GeometryState":
        """创建 `regular-17-e-fixed-v1` 的免费初始状态。"""

        state = cls()
        origin = Point(0, 0)
        start = Point(1, 0)
        state._add_point(origin)
        state._add_point(start)
        state.add_circle(Circle.through(origin, start))
        return state

    @property
    def points(self) -> tuple[Point, ...]:
        return tuple(self._points)

    @property
    def lines(self) -> tuple[Line, ...]:
        return tuple(self._lines)

    @property
    def circles(self) -> tuple[Circle, ...]:
        return tuple(self._circles)

    def contains_point(self, point: Point) -> bool:
        return self._find_equal(self._points, point) is not None

    def contains_line(self, line: Line) -> bool:
        return self._find_equal(self._lines, line) is not None

    def contains_circle(self, circle: Circle) -> bool:
        return self._find_equal(self._circles, circle) is not None

    def draw_line(self, first: Point, second: Point) -> AdditionResult:
        """用状态中的两个点画线并执行自动交点闭包。"""

        self._require_points(first, second)
        return self.add_line(Line.through(first, second))

    def draw_circle(self, center: Point, through: Point) -> AdditionResult:
        """用状态中的两个点画基础圆并执行自动交点闭包。"""

        self._require_points(center, through)
        return self.add_circle(Circle.through(center, through))

    def add_line(self, line: Line) -> AdditionResult:
        """加入精确直线；重复对象不重新求交。"""

        existing = self._find_equal(self._lines, line)
        if existing is not None:
            return AdditionResult(existing, False, (), ())

        results = [intersect(line, old) for old in self._lines]
        results.extend(intersect(line, old) for old in self._circles)
        self._lines.append(line)
        new_points = self._add_intersection_points(results)
        return AdditionResult(line, True, new_points, tuple(results))

    def add_circle(self, circle: Circle) -> AdditionResult:
        """加入精确圆；重复对象不重新求交。"""

        existing = self._find_equal(self._circles, circle)
        if existing is not None:
            return AdditionResult(existing, False, (), ())

        results = [intersect(circle, old) for old in self._lines]
        results.extend(intersect(circle, old) for old in self._circles)
        self._circles.append(circle)
        new_points = self._add_intersection_points(results)
        return AdditionResult(circle, True, new_points, tuple(results))

    def _add_intersection_points(
        self, results: list[IntersectionResult]
    ) -> tuple[Point, ...]:
        new_points: list[Point] = []
        for result in results:
            for point in result.points:
                if self._add_point(point):
                    new_points.append(point)
        return tuple(new_points)

    def _add_point(self, point: Point) -> bool:
        if self.contains_point(point):
            return False
        self._points.append(point)
        return True

    def _require_points(self, *points: Point) -> None:
        for point in points:
            if not self.contains_point(point):
                raise PointNotInStateError("基础操作只能使用当前状态中的点")

    @staticmethod
    def _find_equal(items, candidate):
        for item in items:
            if item == candidate:
                return item
        return None


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
