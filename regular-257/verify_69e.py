"""从公开视频恢复的正 257 边形 69E 构造的快速精确关联检查。

所有高次代数值都放在 ``Q(zeta_257)`` 中，避免反复隔离 ``AA`` 根。每个命名
点都会核对其生成直线或圆；若直线经过圆上的已知点，则用弦中点反射精确恢复
第二交点。
"""

from __future__ import annotations

from dataclasses import dataclass

from sage.all import ComplexField, CyclotomicField


K = CyclotomicField(257)
ZERO = K(0)
ONE = K(1)


@dataclass(frozen=True)
class P:
    x: object
    y: object


@dataclass(frozen=True)
class L:
    a: object
    b: object
    c: object

    def contains(self, point: P) -> bool:
        return self.a * point.x + self.b * point.y + self.c == 0


@dataclass(frozen=True)
class O:
    center: P
    radius2: object

    def contains(self, point: P) -> bool:
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        return dx * dx + dy * dy == self.radius2


def line_through(first: P, second: P) -> L:
    assert first != second
    return L(
        first.y - second.y,
        second.x - first.x,
        first.x * second.y - second.x * first.y,
    )


def circle_through(center: P, through: P) -> O:
    dx = through.x - center.x
    dy = through.y - center.y
    return O(center, dx * dx + dy * dy)


def line_line(first: L, second: L) -> P:
    determinant = first.a * second.b - second.a * first.b
    assert determinant != 0
    return P(
        (first.b * second.c - second.b * first.c) / determinant,
        (first.c * second.a - second.c * first.a) / determinant,
    )


def radical_axis(first: O, second: O) -> L:
    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    return L(
        2 * dx,
        2 * dy,
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius2
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius2,
    )


def other_on_circle(line: L, circle: O, known: P) -> P:
    assert line.contains(known) and circle.contains(known)
    norm2 = line.a * line.a + line.b * line.b
    signed = line.a * circle.center.x + line.b * circle.center.y + line.c
    foot = P(
        circle.center.x - line.a * signed / norm2,
        circle.center.y - line.b * signed / norm2,
    )
    other = P(2 * foot.x - known.x, 2 * foot.y - known.y)
    assert line.contains(other) and circle.contains(other) and other != known
    return other


def periods():
    zeta = K.gen()
    g = [zeta ** pow(3, j, 257) + zeta ** (-pow(3, j, 257)) for j in range(128)]
    f = [g[j] + g[j + 64] for j in range(64)]
    e = [f[j] + f[j + 32] for j in range(32)]
    d = [e[j] + e[j + 16] for j in range(16)]
    c = [d[j] + d[j + 8] for j in range(8)]
    b = [c[j] + c[j + 4] for j in range(4)]
    a = [b[j] + b[j + 2] for j in range(2)]
    named = {
        "H": K(-2),
        "K": K(-4),
        "L": K(4),
        "A0": a[0],
        "A1": a[1],
        "B0": b[0],
        "B1": b[1],
        "B2": b[2],
        "B3": b[3],
        "Ca": c[0] + 2,
        "Cb": c[5] + 2,
        "Cc": c[0] + c[2],
        "Cd": c[1] + c[7],
        "Da": d[0] + d[1] + d[2] + d[5] + 1,
        "Db": d[8] + d[9] + d[10] + d[13] + 1,
        "Dc": d[1] + d[7] - d[0],
        "Dd": d[9] + d[15] - d[8],
        "D0": d[0],
        "D8": d[8],
        "E0": e[0],
        "E24": e[24],
        "F0": f[0],
        "F56": f[56],
        "G0": g[0],
    }
    return zeta, g, f, e, d, c, b, a, named


def encoded_point(value) -> P:
    denominator = value * value + 1
    return P(2 * value / denominator, (1 - value * value) / denominator)


class Check:
    def __init__(self, encoded_values: dict[str, object]) -> None:
        self.encoded_values = encoded_values
        self.points = {"C": P(ZERO, -ONE), "B": P(ZERO, ONE)}
        self.objects = {"c0": circle_through(self.points["C"], self.points["B"])}
        self.lines = 0
        self.circles = 0
        self.steps: list[tuple[int, str, str]] = []

    def line(self, step: int, name: str, first: str, second: str) -> None:
        self.objects[name] = line_through(self.points[first], self.points[second])
        self.lines += 1
        self.steps.append((step, "line", f"{first}{second}"))

    def circle(self, step: int, name: str, center: str, through: str) -> None:
        self.objects[name] = circle_through(self.points[center], self.points[through])
        self.circles += 1
        self.steps.append((step, "circle", f"{center},{through}"))

    def ll(self, name: str, first: str, second: str) -> P:
        point = line_line(self.objects[first], self.objects[second])
        self.points[name] = point
        return point

    def other(self, name: str, line: str, circle: str, known: str) -> P:
        point = other_on_circle(self.objects[line], self.objects[circle], self.points[known])
        self.points[name] = point
        return point

    def expected(self, name: str, line: str, circle: str = "c") -> P:
        point = encoded_point(self.encoded_values[name])
        assert self.objects[line].contains(point), f"{name} is not on {line}"
        assert self.objects[circle].contains(point), f"{name} is not on {circle}"
        self.points[name] = point
        return point

    def expected_pair(self, first_name: str, second_name: str, line: str, circle: str = "c") -> None:
        self.expected(first_name, line, circle)
        self.expected(second_name, line, circle)
        assert self.points[first_name] != self.points[second_name]


def verify() -> tuple[Check, object, object]:
    zeta, g, f, e, dvals, cvals, bvals, avals, named = periods()
    r = Check(named)

    r.line(1, "a", "C", "B")
    r.other("M1", "a", "c0", "B")
    r.circle(2, "q", "B", "C")
    # The two equal radius-2 circles have radical axis y=0 and two real
    # intersections (±sqrt(3), 0).  This is the sole bootstrap outside K.
    r.objects["d"] = radical_axis(r.objects["q"], r.objects["c0"])
    assert r.objects["d"].contains(P(ZERO, ZERO))
    r.lines += 1
    r.steps.append((3, "line", "q∩c0"))
    r.ll("A", "a", "d")
    r.circle(4, "c", "A", "B")
    r.points["D"], r.points["E"] = P(-ONE, ZERO), P(ONE, ZERO)
    assert r.objects["c"].contains(r.points["D"]) and r.objects["d"].contains(r.points["D"])
    assert r.objects["c"].contains(r.points["E"]) and r.objects["d"].contains(r.points["E"])
    r.line(5, "BE", "B", "E")
    r.other("G", "BE", "c0", "B")
    r.line(6, "b", "C", "G")
    r.other("F", "b", "c0", "G")
    r.line(7, "DM1", "D", "M1")
    r.expected("H", "DM1")
    r.ll("I", "DM1", "b")
    r.line(8, "IE", "I", "E")
    r.expected("K", "IE")
    r.ll("J", "IE", "a")
    r.line(9, "DJ", "D", "J")
    r.expected("L", "DJ")
    r.line(10, "KL", "K", "L")
    r.ll("N", "KL", "BE")
    r.ll("M", "KL", "a")
    r.line(11, "NI", "N", "I")
    r.ll("O", "NI", "a")
    assert r.points["M"] == P(ZERO, K(-15) / 17)
    assert r.points["O"] == P(ZERO, K(-63) / 65)
    r.line(12, "FO", "F", "O")
    r.expected_pair("A0", "A1", "FO")
    r.line(13, "BA0", "B", "A0")
    r.ll("R", "BA0", "b")
    r.line(14, "BA1", "B", "A1")
    r.ll("S", "BA1", "b")
    r.line(15, "RM", "R", "M")
    r.expected_pair("B0", "B2", "RM")
    r.line(16, "SM", "S", "M")
    r.expected_pair("B1", "B3", "SM")
    r.line(17, "EA1", "E", "A1")
    r.ll("T", "EA1", "a")
    r.line(18, "LB0", "L", "B0")
    r.ll("U", "LB0", "b")
    r.line(19, "UT", "U", "T")
    r.expected("Ca", "UT")
    r.line(20, "EA0", "E", "A0")
    r.ll("V", "EA0", "a")
    r.line(21, "LB1", "L", "B1")
    r.ll("W", "LB1", "b")
    r.line(22, "VW", "V", "W")
    r.expected("Cb", "VW")
    r.line(23, "B0B3", "B0", "B3")
    r.ll("X", "B0B3", "a")
    r.line(24, "RX", "R", "X")
    r.expected("Cc", "RX")
    r.line(25, "B2B3", "B2", "B3")
    r.ll("Y", "B2B3", "a")
    r.line(26, "YS", "Y", "S")
    r.expected("Cd", "YS")
    r.line(27, "HCa", "H", "Ca")
    r.ll("Z", "HCa", "b")
    r.line(28, "ZK", "Z", "K")
    r.ll("H1", "ZK", "a")
    r.line(29, "B1Cc", "B1", "Cc")
    r.ll("I1", "B1Cc", "b")
    r.line(30, "I1H", "I1", "H")
    r.other("J1", "I1H", "c", "H")
    r.line(31, "BJ1", "B", "J1")
    r.ll("K1", "BJ1", "b")
    r.line(32, "K1H1", "K1", "H1")
    r.expected_pair("Da", "Db", "K1H1")
    r.line(33, "BZ", "B", "Z")
    r.other("L1", "BZ", "c", "B")
    r.circle(34, "circle_M1L1", "M1", "L1")
    axis = radical_axis(r.objects["circle_M1L1"], r.objects["c"])
    r.objects["axis_34"] = axis
    r.points["N1"] = other_on_circle(axis, r.objects["c"], r.points["L1"])
    assert r.objects["circle_M1L1"].contains(r.points["N1"])
    r.line(35, "CdN1", "Cd", "N1")
    r.ll("O1", "CdN1", "b")
    r.line(36, "HCb", "H", "Cb")
    r.ll("P1", "HCb", "a")
    r.line(37, "EP1", "E", "P1")
    r.other("Q1", "EP1", "c", "E")
    r.line(38, "LQ1", "L", "Q1")
    r.ll("R1", "LQ1", "b")
    r.line(39, "R1Cc", "R1", "Cc")
    r.other("S1", "R1Cc", "c", "Cc")
    r.line(40, "CdB0", "Cd", "B0")
    r.ll("T1", "CdB0", "b")
    r.line(41, "T1S1", "T1", "S1")
    r.other("U1", "T1S1", "c", "S1")
    r.line(42, "EU1", "E", "U1")
    r.ll("V1", "EU1", "a")
    r.line(43, "V1O1", "V1", "O1")
    r.expected_pair("Dc", "Dd", "V1O1")
    r.line(44, "RS1", "R", "S1")
    r.other("W1", "RS1", "c", "S1")
    r.line(45, "EW1", "E", "W1")
    r.ll("X1", "EW1", "a")
    r.line(46, "X1Z", "X1", "Z")
    r.expected_pair("D0", "D8", "X1Z")
    r.line(47, "BD0", "B", "D0")
    r.ll("Y1", "BD0", "b")
    r.line(48, "GDa", "G", "Da")
    r.other("Z1", "GDa", "c", "Da")
    r.line(49, "DZ1", "D", "Z1")
    r.ll("H2", "DZ1", "a")
    r.line(50, "H2Y1", "H2", "Y1")
    r.expected("E0", "H2Y1")
    r.line(51, "BE0", "B", "E0")
    r.ll("I2", "BE0", "b")
    r.line(52, "DcD0", "Dc", "D0")
    r.ll("J2", "DcD0", "b")
    # Resolve the visually selected K2 by the later exact F0 incidence.
    r.points["F0"] = encoded_point(named["F0"])
    future_L2 = line_line(line_through(r.points["I2"], r.points["F0"]), r.objects["a"])
    future_K2 = line_line(line_through(r.points["E"], future_L2), line_through(r.points["A"], r.points["J2"]))
    r.line(53, "AJ2", "A", "J2")
    assert r.objects["AJ2"].contains(future_K2) and r.objects["c"].contains(future_K2)
    r.points["K2"] = future_K2
    r.line(54, "EK2", "E", "K2")
    r.ll("L2", "EK2", "a")
    assert r.points["L2"] == future_L2
    r.line(55, "L2I2", "L2", "I2")
    assert r.objects["L2I2"].contains(r.points["F0"])
    r.line(56, "BD8", "B", "D8")
    r.ll("M2", "BD8", "b")
    r.line(57, "GDb", "G", "Db")
    r.other("N2", "GDb", "c", "Db")
    r.line(58, "DN2", "D", "N2")
    r.ll("O2", "DN2", "a")
    r.line(59, "M2O2", "M2", "O2")
    r.expected("E24", "M2O2")
    r.line(60, "BE24", "B", "E24")
    r.ll("P2", "BE24", "b")
    r.line(61, "D8Dd", "D8", "Dd")
    r.ll("Q2", "D8Dd", "b")
    # Resolve the opposite antipode R2 by the later exact F56 incidence.
    r.points["F56"] = encoded_point(named["F56"])
    future_S2 = line_line(line_through(r.points["P2"], r.points["F56"]), r.objects["a"])
    future_R2 = line_line(line_through(r.points["E"], future_S2), line_through(r.points["A"], r.points["Q2"]))
    r.line(62, "AQ2", "A", "Q2")
    assert r.objects["AQ2"].contains(future_R2) and r.objects["c"].contains(future_R2)
    r.points["R2"] = future_R2
    r.line(63, "ER2", "E", "R2")
    r.ll("S2", "ER2", "a")
    assert r.points["S2"] == future_S2
    r.line(64, "S2P2", "S2", "P2")
    assert r.objects["S2P2"].contains(r.points["F56"])
    r.line(65, "BF0", "B", "F0")
    r.ll("T2", "BF0", "b")
    r.line(66, "EF56", "E", "F56")
    r.ll("U2", "EF56", "a")
    r.line(67, "U2T2", "U2", "T2")
    r.expected("G0", "U2T2")
    r.line(68, "BG0", "B", "G0")
    r.ll("V2", "BG0", "b")
    r.circle(69, "target_transfer", "V2", "C")

    # The final circle and c0 have radical axis x=g0.  Hence their two
    # intersections on the radius-2 target circle satisfy X/2=g0/2,
    # i.e. cos(theta) with theta=±2*pi/257 measured from the constructed
    # rightmost radius CG.
    target_axis = radical_axis(r.objects["target_transfer"], r.objects["c0"])
    test = P(named["G0"], -ONE)
    assert target_axis.contains(test)
    assert target_axis.b == 0 and -target_axis.c / target_axis.a == named["G0"]
    assert named["G0"] == zeta + zeta ** -1

    # Independently check every displayed algebraic relation.
    assert avals[0] + avals[1] == -1 and avals[0] * avals[1] == -64
    assert bvals[0] + bvals[2] == avals[0] and bvals[0] * bvals[2] == -16
    assert bvals[1] + bvals[3] == avals[1] and bvals[1] * bvals[3] == -16
    assert (cvals[0] + 2) + (cvals[4] + 2) == bvals[0] + 4
    assert (cvals[0] + 2) * (cvals[4] + 2) == avals[1]
    assert (cvals[1] + 2) + (cvals[5] + 2) == bvals[1] + 4
    assert (cvals[1] + 2) * (cvals[5] + 2) == avals[0]
    assert (cvals[0] + cvals[2]) + (cvals[4] + cvals[6]) == avals[0]
    assert (cvals[0] + cvals[2]) * (cvals[4] + cvals[6]) == bvals[0] * bvals[3]
    assert (cvals[1] + cvals[7]) + (cvals[3] + cvals[5]) == avals[1]
    assert (cvals[1] + cvals[7]) * (cvals[3] + cvals[5]) == bvals[2] * bvals[3]
    da = dvals[0] + dvals[1] + dvals[2] + dvals[5] + 1
    db = dvals[8] + dvals[9] + dvals[10] + dvals[13] + 1
    dc = dvals[1] + dvals[7] - dvals[0]
    dd = dvals[9] + dvals[15] - dvals[8]
    assert da + db == bvals[1] + cvals[0] + cvals[2] + 2
    assert da * db == -4 * cvals[0] - 16
    assert dc + dd == cvals[1] + cvals[7] - cvals[0]
    assert dc * dd == bvals[0] + (cvals[0] + cvals[2] + 2 * cvals[5]) + (cvals[1] + cvals[7])
    assert dvals[0] + dvals[8] == cvals[0]
    assert dvals[0] * dvals[8] == avals[0] + cvals[0] + cvals[2] + 2 * cvals[5]
    assert e[0] + e[16] == dvals[0]
    assert e[0] * e[16] == dvals[0] + dvals[1] + dvals[2] + dvals[5]
    assert (e[1] + e[23]) + (e[7] + e[17]) == dvals[1] + dvals[7]
    assert (e[1] + e[23]) * (e[7] + e[17]) == -1
    assert e[8] + e[24] == dvals[8]
    assert e[8] * e[24] == dvals[8] + dvals[9] + dvals[10] + dvals[13]
    assert (e[9] + e[31]) + (e[15] + e[25]) == dvals[9] + dvals[15]
    assert (e[9] + e[31]) * (e[15] + e[25]) == -1
    assert f[0] + f[32] == e[0] and f[0] * f[32] == e[1] + e[23]
    assert f[24] + f[56] == e[24] and f[24] * f[56] == e[15] + e[25]
    assert g[0] + g[64] == f[0] and g[0] * g[64] == f[56]
    return r, named["G0"], target_axis


def main() -> None:
    replay, g0, target_axis = verify()
    complex_field = ComplexField(120)
    g0_approx = complex_field(g0)
    v2_x_approx = complex_field(replay.points["V2"].x)
    print(f"steps={len(replay.steps)} lines={replay.lines} circles={replay.circles}")
    print(f"g0_approx={g0_approx.real():.30f}")
    print(f"V2_x_approx={v2_x_approx.real():.30f}")
    print(f"target_axis_x_equals_g0={-target_axis.c / target_axis.a == g0}")
    print("exact_incidence_check=true")
    print("displayed_period_relations=true")


if __name__ == "__main__":
    main()
