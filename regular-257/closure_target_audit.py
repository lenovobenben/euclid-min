"""非锚定正 257 边形目标的完整自动闭包审计。

任一自动闭包目标点都位于初始圆 ``c0`` 上。直线与 ``c0`` 的公共点由该直线
承载；另一个圆与 ``c0`` 的公共点由两圆根轴承载。因此无需物化所有偶然交点，
只需审计每个不同作图对象对应的弦载线。

相邻关系通过把载线精确旋转 ``±2*pi/257`` 后求两条线的公共点来判断。为避免
建立昂贵的 512 次数域，本模块直接实现
``Q(zeta_257)[s] / (s^2 - (1-cos(theta)^2))`` 的二次算术。
"""

from __future__ import annotations

from dataclasses import dataclass

from cyclotomic_replay import FIELD, ORDER_FIELD, Circle, Drawable, Line


ZETA = FIELD.gen()
COSINE = (ZETA + ZETA**-1) / 2
SINE_SQUARED = 1 - COSINE * COSINE
TARGET_RADIUS_SQUARED = FIELD(4)


@dataclass(frozen=True)
class Quadratic:
    """精确表示 ``real + sine_coefficient*s``。"""

    real: object
    sine_coefficient: object = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "real", FIELD(self.real))
        object.__setattr__(
            self,
            "sine_coefficient",
            FIELD(self.sine_coefficient),
        )

    def __add__(self, other):
        other = _quadratic(other)
        return Quadratic(
            self.real + other.real,
            self.sine_coefficient + other.sine_coefficient,
        )

    __radd__ = __add__

    def __neg__(self):
        return Quadratic(-self.real, -self.sine_coefficient)

    def __sub__(self, other):
        return self + (-_quadratic(other))

    def __rsub__(self, other):
        return _quadratic(other) - self

    def __mul__(self, other):
        other = _quadratic(other)
        return Quadratic(
            self.real * other.real
            + self.sine_coefficient
            * other.sine_coefficient
            * SINE_SQUARED,
            self.real * other.sine_coefficient
            + self.sine_coefficient * other.real,
        )

    __rmul__ = __mul__

    def inverse(self):
        denominator = (
            self.real * self.real
            - self.sine_coefficient
            * self.sine_coefficient
            * SINE_SQUARED
        )
        if denominator == 0:
            raise ZeroDivisionError("二次扩域元素为零")
        return Quadratic(
            self.real / denominator,
            -self.sine_coefficient / denominator,
        )

    def __truediv__(self, other):
        return self * _quadratic(other).inverse()

    def __rtruediv__(self, other):
        return _quadratic(other) / self

    def __eq__(self, other):
        try:
            other = _quadratic(other)
        except (TypeError, ValueError):
            return False
        return (
            self.real == other.real
            and self.sine_coefficient == other.sine_coefficient
        )


def _quadratic(value) -> Quadratic:
    if isinstance(value, Quadratic):
        return value
    return Quadratic(value)


@dataclass(frozen=True)
class Carrier:
    """目标圆中心坐标系中的规范化直线 ``a*x+b*y+d=0``。"""

    a: object
    b: object
    d: object

    def __post_init__(self) -> None:
        a = FIELD(self.a)
        b = FIELD(self.b)
        d = FIELD(self.d)
        if a == 0 and b == 0:
            raise ValueError("弦载线系数不能同时为零")
        scale = a if a != 0 else b
        object.__setattr__(self, "a", a / scale)
        object.__setattr__(self, "b", b / scale)
        object.__setattr__(self, "d", d / scale)


@dataclass(frozen=True)
class QuadraticLine:
    a: Quadratic
    b: Quadratic
    d: Quadratic


@dataclass(frozen=True)
class TargetHit:
    e_move: int
    new_object: str
    source_object: str
    orientation: str


@dataclass(frozen=True)
class TargetAuditResult:
    distinct_lines: int
    distinct_circles: int
    duplicate_draws: int
    first_target_e_move: int | None
    first_hits: tuple[TargetHit, ...]


def carrier_for(drawable: Drawable, target_circle: Circle) -> Carrier | None:
    """返回对象与目标圆公共点的载线；重合圆返回 ``None``。"""

    if isinstance(drawable, Line):
        # 全局 y = centered_y - 1。
        return Carrier(drawable.a, drawable.b, drawable.c - drawable.b)
    if not isinstance(drawable, Circle):
        raise TypeError("只支持直线和圆")
    if drawable == target_circle:
        return None

    center_x = drawable.center.x - target_circle.center.x
    center_y = drawable.center.y - target_circle.center.y
    return Carrier(
        -2 * center_x,
        -2 * center_y,
        center_x * center_x
        + center_y * center_y
        - drawable.radius_squared
        + target_circle.radius_squared,
    )


def rotate_carrier(carrier: Carrier, orientation: int) -> QuadraticLine:
    """返回点集按 ``orientation*theta`` 旋转后的载线。"""

    if orientation not in (-1, 1):
        raise ValueError("orientation 必须为 -1 或 1")
    return QuadraticLine(
        Quadratic(carrier.a * COSINE, -orientation * carrier.b),
        Quadratic(carrier.b * COSINE, orientation * carrier.a),
        Quadratic(carrier.d),
    )


def carriers_have_adjacent_points(
    source: Carrier,
    destination: Carrier,
    orientation: int,
) -> bool:
    """判断两个载线是否承载相差指定方向中心角的圆上点。"""

    if orientation not in (-1, 1):
        raise ValueError("orientation 必须为 -1 或 1")

    # 旋转载线系数为：
    # alpha=a*c-orientation*b*s, beta=b*c+orientation*a*s。
    # 与 A*x+B*y+D=0 求交，把 determinant、x/y 分子分别写成
    # real+sine_coefficient*s，随后比较圆方程的两个主域系数。
    a, b, d = source.a, source.b, source.d
    A, B, D = destination.a, destination.b, destination.d
    determinant_real = COSINE * (a * B - A * b)
    determinant_sine = -orientation * (b * B + A * a)
    if determinant_real == 0 and determinant_sine == 0:
        if not _rotated_carrier_coincides(
            source,
            destination,
            orientation,
        ):
            return False
        return _carrier_has_real_target_circle_point(destination)

    x_real = b * COSINE * D - B * d
    x_sine = orientation * a * D
    y_real = d * A - D * a * COSINE
    y_sine = orientation * D * b

    circle_real = (
        x_real * x_real
        + x_sine * x_sine * SINE_SQUARED
        + y_real * y_real
        + y_sine * y_sine * SINE_SQUARED
        - TARGET_RADIUS_SQUARED
        * (
            determinant_real * determinant_real
            + determinant_sine * determinant_sine * SINE_SQUARED
        )
    )
    circle_sine = 2 * (
        x_real * x_sine
        + y_real * y_sine
        - TARGET_RADIUS_SQUARED
        * determinant_real
        * determinant_sine
    )
    return circle_real == 0 and circle_sine == 0


def carrier_contains_initial_adjacent_point(
    carrier: Carrier,
    orientation: int,
) -> bool:
    """判断载线是否经过初始点 B 旋转指定中心角后的点。"""

    # 目标圆中心坐标中 B=(0,2)。
    real = 2 * carrier.b * COSINE + carrier.d
    sine_coefficient = -2 * orientation * carrier.a
    return real == 0 and sine_coefficient == 0


def _coincident(first: QuadraticLine, second: QuadraticLine) -> bool:
    return (
        first.a * second.d == second.a * first.d
        and first.b * second.d == second.b * first.d
    )


def _rotated_carrier_coincides(
    source: Carrier,
    destination: Carrier,
    orientation: int,
) -> bool:
    a, b, d = source.a, source.b, source.d
    A, B, D = destination.a, destination.b, destination.d
    return (
        a * COSINE * D == A * d
        and -orientation * b * D == 0
        and b * COSINE * D == B * d
        and orientation * a * D == 0
    )


def _carrier_has_real_target_circle_point(carrier: Carrier) -> bool:
    discriminant = (
        TARGET_RADIUS_SQUARED
        * (carrier.a * carrier.a + carrier.b * carrier.b)
        - carrier.d * carrier.d
    )
    return ORDER_FIELD(discriminant) >= 0


class ClosureTargetAuditor:
    """按计费对象顺序做精确去重和完整目标闭包审计。"""

    def __init__(self, target_circle: Circle) -> None:
        self.target_circle = target_circle
        self._seen_drawables: list[tuple[str, Drawable]] = [
            ("c0", target_circle)
        ]
        self._drawables: list[tuple[str, Drawable]] = []
        self._carriers: list[tuple[str, Carrier]] = []
        self.duplicate_draws = 0
        self.first_target_e_move: int | None = None
        self.first_hits: list[TargetHit] = []

    def add_drawable(
        self,
        name: str,
        drawable: Drawable,
        e_move: int,
    ) -> bool:
        """加入一个计费对象；返回它是否为新的数学对象。"""

        for _old_name, old in self._seen_drawables:
            if type(old) is type(drawable) and old == drawable:
                self.duplicate_draws += 1
                return False
        self._seen_drawables.append((name, drawable))
        self._drawables.append((name, drawable))

        carrier = carrier_for(drawable, self.target_circle)
        if carrier is None:
            return True
        hits = self._new_hits(name, carrier, e_move)
        self._carriers.append((name, carrier))
        if hits and self.first_target_e_move is None:
            self.first_target_e_move = e_move
            self.first_hits.extend(hits)
        return True

    def result(self) -> TargetAuditResult:
        return TargetAuditResult(
            distinct_lines=sum(
                isinstance(drawable, Line)
                for _name, drawable in self._drawables
            ),
            distinct_circles=sum(
                isinstance(drawable, Circle)
                for _name, drawable in self._drawables
            ),
            duplicate_draws=self.duplicate_draws,
            first_target_e_move=self.first_target_e_move,
            first_hits=tuple(self.first_hits),
        )

    def _new_hits(
        self,
        name: str,
        carrier: Carrier,
        e_move: int,
    ) -> list[TargetHit]:
        hits: list[TargetHit] = []
        for orientation in (-1, 1):
            label = "minus" if orientation == -1 else "plus"
            if carrier_contains_initial_adjacent_point(carrier, orientation):
                hits.append(TargetHit(e_move, name, "B", label))
            if carriers_have_adjacent_points(
                carrier,
                carrier,
                orientation,
            ):
                hits.append(TargetHit(e_move, name, name, label))
            for old_name, old_carrier in self._carriers:
                if carriers_have_adjacent_points(
                    old_carrier,
                    carrier,
                    orientation,
                ):
                    hits.append(TargetHit(e_move, name, old_name, label))
        return hits
