"""把 69E 几何证书编译为带上下文 E 成本的几何—代数统一 IR。"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from cyclotomic_replay import Circle, ORDER_FIELD, Point
from semantic_dependency import exact_replay_universe
from verify_69e import periods


def _const(value: int) -> dict:
    return {"op": "const", "value": value}


def _symbol(symbol_id: str) -> dict:
    return {"op": "symbol", "id": symbol_id}


def _expression(value: dict | int | str) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, int):
        return _const(value)
    if isinstance(value, str):
        return _symbol(value)
    raise TypeError(f"不支持的表达式节点: {value!r}")


def _add(*args: dict | int | str) -> dict:
    return {"op": "add", "args": [_expression(arg) for arg in args]}


def _mul(*args: dict | int | str) -> dict:
    return {"op": "mul", "args": [_expression(arg) for arg in args]}


def _neg(arg: dict | int | str) -> dict:
    return {"op": "neg", "arg": _expression(arg)}


def _sub(left: dict | int | str, right: dict | int | str) -> dict:
    return _add(left, _neg(right))


def _div(
    numerator: dict | int | str,
    denominator: dict | int | str,
) -> dict:
    return {
        "op": "div",
        "numerator": _expression(numerator),
        "denominator": _expression(denominator),
    }


def expression_symbol_ids(expression: dict) -> set[str]:
    operation = expression["op"]
    if operation == "const":
        return set()
    if operation == "symbol":
        return {expression["id"]}
    if operation in {"add", "mul"}:
        return set().union(
            *(expression_symbol_ids(arg) for arg in expression["args"])
        )
    if operation == "neg":
        return expression_symbol_ids(expression["arg"])
    if operation == "div":
        return expression_symbol_ids(expression["numerator"]) | expression_symbol_ids(
            expression["denominator"]
        )
    raise ValueError(f"未知表达式操作: {operation!r}")


def evaluate_expression(expression: dict, values: dict[str, object]):
    operation = expression["op"]
    if operation == "const":
        return ORDER_FIELD(expression["value"])
    if operation == "symbol":
        return ORDER_FIELD(values[expression["id"]])
    if operation == "add":
        return sum(
            (evaluate_expression(arg, values) for arg in expression["args"]),
            ORDER_FIELD(0),
        )
    if operation == "mul":
        result = ORDER_FIELD(1)
        for arg in expression["args"]:
            result *= evaluate_expression(arg, values)
        return result
    if operation == "neg":
        return -evaluate_expression(expression["arg"], values)
    if operation == "div":
        denominator = evaluate_expression(expression["denominator"], values)
        if denominator == 0:
            raise ZeroDivisionError("GA-IR 表达式出现零分母")
        return evaluate_expression(expression["numerator"], values) / denominator
    raise ValueError(f"未知表达式操作: {operation!r}")


def _algebra_system() -> tuple[list[dict], list[dict], dict[str, object]]:
    """建立视频代数主干的结构化二次关系，并在分圆域中逐式核对。"""

    _zeta, g, f, e, d, c, b, a, _named = periods()
    values: dict[str, object] = {}
    symbols: list[dict] = []
    relations: list[dict] = []

    def add_constant(symbol_id: str, value: int, description: str) -> None:
        values[symbol_id] = ORDER_FIELD(value)
        symbols.append(
            {
                "id": symbol_id,
                "kind": "constant",
                "description": description,
            }
        )

    for symbol_id, value, description in (
        ("constant.zero", 0, "编码圆上的 0"),
        ("constant.minus_one", -1, "编码圆上的 -1"),
        ("constant.one", 1, "编码圆上的 1"),
        ("constant.minus_two", -2, "编码圆上的 -2"),
        ("constant.minus_four", -4, "编码圆上的 -4"),
        ("constant.four", 4, "编码圆上的 4"),
    ):
        add_constant(symbol_id, value, description)

    def add_root_pair(
        relation_id: str,
        roots: tuple[tuple[str, object, str], tuple[str, object, str]],
        root_sum: dict,
        root_product: dict,
        materialized: Iterable[tuple[str, str]],
    ) -> None:
        root_ids = []
        for symbol_id, value, description in roots:
            if symbol_id in values:
                raise ValueError(f"代数符号重复: {symbol_id}")
            values[symbol_id] = value
            root_ids.append(symbol_id)
            symbols.append(
                {
                    "id": symbol_id,
                    "kind": "quadratic_root",
                    "description": description,
                    "producer_relation": relation_id,
                }
            )
        left = ORDER_FIELD(values[root_ids[0]])
        right = ORDER_FIELD(values[root_ids[1]])
        if left + right != evaluate_expression(root_sum, values):
            raise ValueError(f"{relation_id} 的根和不成立")
        if left * right != evaluate_expression(root_product, values):
            raise ValueError(f"{relation_id} 的根积不成立")
        materialized_records = [
            {"symbol": symbol_id, "point": point}
            for symbol_id, point in materialized
        ]
        if any(record["symbol"] not in root_ids for record in materialized_records):
            raise ValueError(f"{relation_id} 的物化根不属于该根对")
        relations.append(
            {
                "id": relation_id,
                "kind": "quadratic_root_pair",
                "roots": root_ids,
                "sum": root_sum,
                "product": root_product,
                "materialized_roots": materialized_records,
                "verified": True,
            }
        )

    add_root_pair(
        "relation.a",
        (
            ("period.a0", a[0], "高斯周期 a_0"),
            ("period.a1", a[1], "高斯周期 a_1"),
        ),
        _const(-1),
        _const(-64),
        (("period.a0", "A0"), ("period.a1", "A1")),
    )
    add_root_pair(
        "relation.b-even",
        (
            ("period.b0", b[0], "高斯周期 b_0"),
            ("period.b2", b[2], "高斯周期 b_2"),
        ),
        _symbol("period.a0"),
        _const(-16),
        (("period.b0", "B0"), ("period.b2", "B2")),
    )
    add_root_pair(
        "relation.b-odd",
        (
            ("period.b1", b[1], "高斯周期 b_1"),
            ("period.b3", b[3], "高斯周期 b_3"),
        ),
        _symbol("period.a1"),
        _const(-16),
        (("period.b1", "B1"), ("period.b3", "B3")),
    )
    add_root_pair(
        "relation.c-a",
        (
            ("work.ca", c[0] + 2, "移位周期 c_0+2"),
            ("work.ca-conjugate", c[4] + 2, "共轭移位周期 c_4+2"),
        ),
        _add("period.b0", 4),
        _symbol("period.a1"),
        (("work.ca", "Ca"),),
    )
    add_root_pair(
        "relation.c-b",
        (
            ("work.cb-conjugate", c[1] + 2, "共轭移位周期 c_1+2"),
            ("work.cb", c[5] + 2, "移位周期 c_5+2"),
        ),
        _add("period.b1", 4),
        _symbol("period.a0"),
        (("work.cb", "Cb"),),
    )
    add_root_pair(
        "relation.c-c",
        (
            ("work.cc", c[0] + c[2], "周期和 c_0+c_2"),
            ("work.cc-conjugate", c[4] + c[6], "共轭周期和 c_4+c_6"),
        ),
        _symbol("period.a0"),
        _mul("period.b0", "period.b3"),
        (("work.cc", "Cc"),),
    )
    add_root_pair(
        "relation.c-d",
        (
            ("work.cd", c[1] + c[7], "周期和 c_1+c_7"),
            ("work.cd-conjugate", c[3] + c[5], "共轭周期和 c_3+c_5"),
        ),
        _symbol("period.a1"),
        _mul("period.b2", "period.b3"),
        (("work.cd", "Cd"),),
    )

    da = d[0] + d[1] + d[2] + d[5] + 1
    db = d[8] + d[9] + d[10] + d[13] + 1
    dc = d[1] + d[7] - d[0]
    dd = d[9] + d[15] - d[8]
    add_root_pair(
        "relation.d-ab",
        (
            ("work.da", da, "d 层辅助量 Da"),
            ("work.db", db, "d 层辅助量 Db"),
        ),
        _add("period.b1", "work.cc", 2),
        _add(_mul(-4, "work.ca"), -8),
        (("work.da", "Da"), ("work.db", "Db")),
    )
    add_root_pair(
        "relation.d-cd",
        (
            ("work.dc", dc, "d 层辅助量 Dc"),
            ("work.dd", dd, "d 层辅助量 Dd"),
        ),
        _add("work.cd", _neg("work.ca"), 2),
        _add("period.b0", "work.cc", _mul(2, "work.cb"), "work.cd", -4),
        (("work.dc", "Dc"), ("work.dd", "Dd")),
    )
    add_root_pair(
        "relation.d-main",
        (
            ("period.d0", d[0], "高斯周期 d_0"),
            ("period.d8", d[8], "高斯周期 d_8"),
        ),
        _sub("work.ca", 2),
        _add("period.a0", "work.cc", _mul(2, "work.cb"), -4),
        (("period.d0", "D0"), ("period.d8", "D8")),
    )
    add_root_pair(
        "relation.e-low-aux",
        (
            ("work.e-low-0", e[1] + e[23], "e_1+e_23"),
            ("work.e-low-1", e[7] + e[17], "e_7+e_17"),
        ),
        _add("work.dc", "period.d0"),
        _const(-1),
        (("work.e-low-0", "K2"),),
    )
    add_root_pair(
        "relation.e0",
        (
            ("period.e0", e[0], "高斯周期 e_0"),
            ("period.e16", e[16], "高斯周期 e_16"),
        ),
        _symbol("period.d0"),
        _sub("work.da", 1),
        (("period.e0", "E0"),),
    )
    add_root_pair(
        "relation.f0",
        (
            ("period.f0", f[0], "高斯周期 f_0"),
            ("period.f32", f[32], "高斯周期 f_32"),
        ),
        _symbol("period.e0"),
        _symbol("work.e-low-0"),
        (("period.f0", "F0"),),
    )
    add_root_pair(
        "relation.e-high-aux",
        (
            ("work.e-high-0", e[9] + e[31], "e_9+e_31"),
            ("work.e-high-1", e[15] + e[25], "e_15+e_25"),
        ),
        _add("work.dd", "period.d8"),
        _const(-1),
        (("work.e-high-1", "R2"),),
    )
    add_root_pair(
        "relation.e24",
        (
            ("period.e8", e[8], "高斯周期 e_8"),
            ("period.e24", e[24], "高斯周期 e_24"),
        ),
        _symbol("period.d8"),
        _sub("work.db", 1),
        (("period.e24", "E24"),),
    )
    add_root_pair(
        "relation.f56",
        (
            ("period.f24", f[24], "高斯周期 f_24"),
            ("period.f56", f[56], "高斯周期 f_56"),
        ),
        _symbol("period.e24"),
        _symbol("work.e-high-1"),
        (("period.f56", "F56"),),
    )
    add_root_pair(
        "relation.g0",
        (
            ("period.g0", g[0], "g_0=zeta+zeta^-1"),
            ("period.g64", g[64], "共轭周期 g_64"),
        ),
        _symbol("period.f0"),
        _symbol("period.f56"),
        (("period.g0", "G0"),),
    )

    v2_expression = _div(2, "period.g0")
    values["coordinate.v2-x"] = evaluate_expression(v2_expression, values)
    symbols.append(
        {
            "id": "coordinate.v2-x",
            "kind": "derived_expression",
            "description": "点 V2 在基线 b 上的 x 坐标 2/g_0",
            "expression": v2_expression,
        }
    )

    symbol_ids = set(values)
    for relation in relations:
        references = expression_symbol_ids(relation["sum"])
        references |= expression_symbol_ids(relation["product"])
        if not references <= symbol_ids:
            raise ValueError(
                f"{relation['id']} 引用了未知符号: {sorted(references - symbol_ids)}"
            )
    return symbols, relations, values


def _drawable_definition(entry: dict) -> list[str]:
    if entry["op"] == "line":
        return list(entry["through"])
    if entry["op"] == "circle":
        return [entry["center"], entry["through"]]
    raise ValueError(f"不是付费作图: {entry['op']}")


def _birth_schedule(full_report: dict) -> tuple[dict[str, int], dict[str, str]]:
    drawable_times = {"c0": 0}
    for drawable in full_report["arrangement"]["drawables"]:
        drawable_times[drawable["id"]] = drawable["e_move"]

    birth_by_point: dict[str, int] = {}
    alias_to_point: dict[str, str] = {}
    for point in full_report["arrangement"]["points"]:
        point_id = point["id"]
        incident_times = sorted(
            {drawable_times[name] for name in point["incident_drawables"]}
        )
        if point_id in {"B", "C"}:
            birth = 0
        else:
            if len(incident_times) < 2:
                raise ValueError(f"安排点 {point_id} 没有两个不同的生产对象")
            birth = incident_times[1]
        birth_by_point[point_id] = birth
        for alias in [point_id, *point["names"]]:
            old = alias_to_point.setdefault(alias, point_id)
            if old != point_id:
                raise ValueError(f"点别名 {alias} 同时指向 {old} 和 {point_id}")
    return birth_by_point, alias_to_point


def _radical_axis_x(first: Circle, second: Circle):
    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    a = 2 * dx
    b = 2 * dy
    c = (
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius_squared
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius_squared
    )
    if a == 0 or b != 0:
        raise ValueError("目标根轴不是竖直直线")
    return -c / a


def _baseline_macro_partition(
    transitions: list[dict],
    representations: list[dict],
    symbol_ids: set[str],
) -> list[dict]:
    """把固定 69E 顺序切成首批可替换宏；成本仍取自实际几何步骤。"""

    specifications = [
        (
            "macro.bootstrap",
            1,
            9,
            ["constant.zero"],
            [
                "constant.minus_one",
                "constant.one",
                "constant.minus_two",
                "constant.minus_four",
                "constant.four",
            ],
            "建立编码圆、两条坐标轴与基础整数。",
        ),
        (
            "macro.a-pair",
            10,
            12,
            [
                "constant.minus_one",
                "constant.minus_two",
                "constant.minus_four",
                "constant.four",
            ],
            ["period.a0", "period.a1"],
            "共同产生 a 层两个根。",
        ),
        (
            "macro.b-pairs-joint",
            13,
            16,
            ["period.a0", "period.a1"],
            ["period.b0", "period.b1", "period.b2", "period.b3"],
            "两组 b 层根共享基线与既有辅助痕迹，四笔合并计价。",
        ),
        (
            "macro.c-layer",
            17,
            26,
            [
                "period.a0",
                "period.a1",
                "period.b0",
                "period.b1",
                "period.b2",
                "period.b3",
            ],
            [
                "work.ca",
                "work.ca-conjugate",
                "work.cb-conjugate",
                "work.cb",
                "work.cc",
                "work.cc-conjugate",
                "work.cd",
                "work.cd-conjugate",
            ],
            "连续生成四个 c 层工作量；不把十笔拆成四个固定单价。",
        ),
        (
            "macro.d-ab",
            27,
            32,
            ["period.b1", "work.ca", "work.cc"],
            ["work.da", "work.db"],
            "产生 d 层第一对辅助根。",
        ),
        (
            "macro.d-cd",
            33,
            43,
            ["period.b0", "work.ca", "work.cb", "work.cc", "work.cd"],
            ["work.dc", "work.dd"],
            "包含一次圆作图的 d 层第二对辅助根。",
        ),
        (
            "macro.d-main",
            44,
            46,
            ["period.a0", "work.ca", "work.cb", "work.cc"],
            ["period.d0", "period.d8"],
            "共同产生 d_0 与 d_8。",
        ),
        (
            "macro.low-tail",
            47,
            55,
            ["work.da", "work.dc", "period.d0"],
            [
                "period.e0",
                "period.e16",
                "work.e-low-0",
                "work.e-low-1",
                "period.f0",
                "period.f32",
            ],
            "低半支从 d 层推进到 f_0，并显式识别 K2 的代数值。",
        ),
        (
            "macro.high-tail",
            56,
            64,
            ["work.db", "work.dd", "period.d8"],
            [
                "period.e8",
                "period.e24",
                "work.e-high-0",
                "work.e-high-1",
                "period.f24",
                "period.f56",
            ],
            "高半支从 d 层推进到 f_56，并显式识别 R2 的代数值。",
        ),
        (
            "macro.g0",
            65,
            67,
            ["period.f0", "period.f56"],
            ["period.g0", "period.g64"],
            "由最后一组二次关系取得目标迹 g_0。",
        ),
        (
            "macro.target-transfer",
            68,
            69,
            ["period.g0"],
            ["coordinate.v2-x", "period.g0"],
            "把编码圆上的 g_0 转成目标圆上的竖直根轴。",
        ),
    ]
    macros = []
    covered_drawables = []
    for macro_id, first_e, last_e, inputs, outputs, interpretation in specifications:
        if not set(inputs + outputs) <= symbol_ids:
            missing = set(inputs + outputs) - symbol_ids
            raise ValueError(f"宏 {macro_id} 引用了未知符号: {sorted(missing)}")
        selected = transitions[first_e - 1 : last_e]
        if [item["e_move"] for item in selected] != list(range(first_e, last_e + 1)):
            raise ValueError(f"宏 {macro_id} 的 E 区间不连续")
        paid_drawables = [item["drawable"] for item in selected]
        covered_drawables.extend(paid_drawables)
        output_representations = sorted(
            representation["id"]
            for representation in representations
            if representation["symbol"] in outputs
            and first_e <= representation["available_e_move"] <= last_e
        )
        macros.append(
            {
                "id": macro_id,
                "first_e_move": first_e,
                "last_e_move": last_e,
                "observed_contextual_cost_e": len(selected),
                "paid_drawables": paid_drawables,
                "input_symbols": inputs,
                "output_symbols": outputs,
                "output_representations": output_representations,
                "interpretation": interpretation,
            }
        )
    if covered_drawables != [item["drawable"] for item in transitions]:
        raise ValueError("基线宏没有按顺序恰好覆盖 69 个付费对象")
    return macros


def build_geometry_algebra_ir(
    certificate: dict,
    full_report: dict,
    source: dict,
) -> dict:
    """构建并精确自检 69E GA-IR；不执行文件读写。"""

    if full_report["source"]["construction_sha256"] != certificate["integrity"][
        "construction_sha256"
    ]:
        raise ValueError("完整交点闭包与证书 construction 哈希不一致")
    if full_report["summary"]["unique_finite_real_points"] != 2287:
        raise ValueError("完整交点闭包点数不是已冻结的 2287")

    replay = exact_replay_universe(certificate)
    replayer = replay["replayer"]
    names = replayer.names
    symbols, relations, symbol_values = _algebra_system()
    symbol_ids = {symbol["id"] for symbol in symbols}
    birth_by_point, alias_to_point = _birth_schedule(full_report)

    program = certificate["construction"]["program"]
    paid_entries = [entry for entry in program if entry["op"] != "intersect"]
    if len(paid_entries) != 69:
        raise ValueError("证书付费步骤不是 69")
    if [entry["id"] for entry in paid_entries] != [
        drawable["id"] for drawable in full_report["arrangement"]["drawables"]
    ]:
        raise ValueError("证书与完整交点闭包的付费对象顺序不一致")

    explicit_by_e: dict[int, list[str]] = defaultdict(list)
    explicit_binding_e: dict[str, int] = {}
    current_e = 0
    for entry in program:
        if entry["op"] == "intersect":
            explicit_by_e[current_e].append(entry["id"])
            explicit_binding_e[entry["id"]] = current_e
        else:
            current_e += 1
    if current_e != 69 or len(explicit_binding_e) != 81:
        raise ValueError("证书的付费或免费绑定数量不一致")

    for name, bound_e in explicit_binding_e.items():
        arrangement_id = alias_to_point[name]
        if birth_by_point[arrangement_id] > bound_e:
            raise ValueError(f"点 {name} 的安排出生时刻晚于显式绑定")

    representations: list[dict] = []

    def add_point_representation(
        point_reference: str,
        arrangement_id: str,
        point,
        symbol_id: str,
        chart: str,
        actual_value,
        *,
        representation_id: str,
        bound_e_move: int | None = None,
    ) -> None:
        if symbol_id not in symbol_ids:
            raise ValueError(f"点 {point_reference} 引用了未知代数符号 {symbol_id}")
        if ORDER_FIELD(actual_value) != ORDER_FIELD(symbol_values[symbol_id]):
            raise ValueError(f"点 {point_reference} 的 {chart} 表示值不正确")
        record = {
            "id": representation_id,
            "symbol": symbol_id,
            "carrier": {
                "kind": "point",
                "references": [point_reference],
                "arrangement_point_id": arrangement_id,
            },
            "chart": chart,
            "available_e_move": birth_by_point[arrangement_id],
            "verification": "exact_cyclotomic_equality",
        }
        if bound_e_move is not None:
            record["bound_e_move"] = bound_e_move
        representations.append(record)

    encoding_circle = names["c"]
    named_encoded_points = [
        ("B", "constant.zero"),
        ("D", "constant.minus_one"),
        ("E", "constant.one"),
        ("H", "constant.minus_two"),
        ("K", "constant.minus_four"),
        ("L", "constant.four"),
    ]
    seen_encoded_representations = set()
    for point_name, symbol_id in named_encoded_points:
        point = names[point_name]
        if not encoding_circle.contains(point) or point.y + 1 == 0:
            raise ValueError(f"点 {point_name} 不在编码图 phi 的定义域")
        add_point_representation(
            point_name,
            alias_to_point[point_name],
            point,
            symbol_id,
            "encoding-circle-phi",
            point.x / (point.y + 1),
            representation_id=f"repr.{point_name}",
            bound_e_move=replayer.bound_point_e_moves[point_name],
        )
        seen_encoded_representations.add(symbol_id)

    relation_carriers = {
        "relation.a": "FO",
        "relation.b-even": "RM",
        "relation.b-odd": "SM",
        "relation.c-a": "UT",
        "relation.c-b": "VW",
        "relation.c-c": "RX",
        "relation.c-d": "YS",
        "relation.d-ab": "K1H1",
        "relation.d-cd": "V1O1",
        "relation.d-main": "X1Z",
        "relation.e-low-aux": "AJ2",
        "relation.e0": "H2Y1",
        "relation.f0": "L2I2",
        "relation.e-high-aux": "AQ2",
        "relation.e24": "M2O2",
        "relation.f56": "S2P2",
        "relation.g0": "U2T2",
    }
    arrangement_points = full_report["arrangement"]["points"]
    for relation in relations:
        carrier_name = relation_carriers[relation["id"]]
        carrier = names[carrier_name]
        exact_root_points = {}
        for root_symbol in relation["roots"]:
            value = symbol_values[root_symbol]
            denominator = value * value + 1
            point = Point(
                2 * value / denominator,
                (1 - value * value) / denominator,
            )
            if not carrier.contains(point) or not encoding_circle.contains(point):
                raise ValueError(
                    f"关系 {relation['id']} 的根 {root_symbol} 不在声明载线与编码圆上"
                )
            exact_root_points[root_symbol] = point
        if exact_root_points[relation["roots"][0]] == exact_root_points[
            relation["roots"][1]
        ]:
            raise ValueError(f"关系 {relation['id']} 的两个根点重合")
        candidate_records = [
            record
            for record in arrangement_points
            if carrier_name in record["incident_drawables"]
            and "c" in record["incident_drawables"]
        ]
        if len(candidate_records) != 2:
            raise ValueError(
                f"关系 {relation['id']} 在完整安排中没有恰好两个根点"
            )

        named_by_symbol = {
            record["symbol"]: record["point"]
            for record in relation["materialized_roots"]
        }
        assigned_arrangement_ids = set()
        for root_symbol in relation["roots"]:
            point = exact_root_points[root_symbol]
            if root_symbol in named_by_symbol:
                point_reference = named_by_symbol[root_symbol]
                if names[point_reference] != point:
                    raise ValueError(f"具名根 {point_reference} 与载线交点不一致")
                arrangement_id = alias_to_point[point_reference]
                representation_id = f"repr.{point_reference}"
                bound_e = replayer.bound_point_e_moves[point_reference]
            else:
                remaining = [
                    record["id"]
                    for record in candidate_records
                    if record["id"] not in assigned_arrangement_ids
                    and not any(
                        alias_to_point.get(named_point) == record["id"]
                        for named_point in named_by_symbol.values()
                    )
                ]
                if len(remaining) != 1:
                    raise ValueError(
                        f"关系 {relation['id']} 的未命名根不能唯一落到安排点"
                    )
                arrangement_id = remaining[0]
                point_reference = arrangement_id
                representation_id = f"repr.auto.{root_symbol}"
                bound_e = None
                relation["materialized_roots"].append(
                    {"symbol": root_symbol, "point": arrangement_id}
                )
            if arrangement_id in assigned_arrangement_ids:
                raise ValueError(f"关系 {relation['id']} 的两个根落到同一个安排点")
            assigned_arrangement_ids.add(arrangement_id)
            if root_symbol in seen_encoded_representations:
                raise ValueError(f"代数根 {root_symbol} 被重复表示")
            add_point_representation(
                point_reference,
                arrangement_id,
                point,
                root_symbol,
                "encoding-circle-phi",
                point.x / (point.y + 1),
                representation_id=representation_id,
                bound_e_move=bound_e,
            )
            seen_encoded_representations.add(root_symbol)

    v2 = names["V2"]
    if not names["b"].contains(v2):
        raise ValueError("V2 不在基线 b 上")
    add_point_representation(
        "V2",
        alias_to_point["V2"],
        v2,
        "coordinate.v2-x",
        "baseline-x",
        v2.x,
        representation_id="repr.V2",
        bound_e_move=replayer.bound_point_e_moves["V2"],
    )

    target_circle = names["target_transfer"]
    initial_circle = names["c0"]
    if not isinstance(target_circle, Circle) or not isinstance(initial_circle, Circle):
        raise ValueError("最终对象或初始对象不是圆")
    target_axis_x = _radical_axis_x(target_circle, initial_circle)
    if ORDER_FIELD(target_axis_x) != ORDER_FIELD(symbol_values["period.g0"]):
        raise ValueError("最终根轴没有承载 g0")
    representations.append(
        {
            "id": "repr.target-axis-g0",
            "symbol": "period.g0",
            "carrier": {
                "kind": "radical_axis",
                "references": ["target_transfer", "c0"],
            },
            "chart": "vertical-carrier-x",
            "available_e_move": 69,
            "verification": "exact_cyclotomic_equality",
        }
    )

    representation_ids = {item["id"] for item in representations}
    if len(representation_ids) != len(representations):
        raise ValueError("代数表示 ID 重复")
    representation_by_e: dict[int, list[str]] = defaultdict(list)
    for representation in representations:
        representation_by_e[representation["available_e_move"]].append(
            representation["id"]
        )

    free_points_by_e: dict[int, list[str]] = defaultdict(list)
    for point in full_report["arrangement"]["points"]:
        birth = birth_by_point[point["id"]]
        if birth > 0:
            free_points_by_e[birth].append(point["id"])
    if sum(map(len, free_points_by_e.values())) != 2285:
        raise ValueError("付费步骤后的免费点总数不是 2285")

    definition_uses: Counter[str] = Counter()
    transitions = []
    all_definitions_causal = True
    for e_move, entry in enumerate(paid_entries, start=1):
        definition = _drawable_definition(entry)
        definition_births = []
        for point_name in definition:
            arrangement_id = alias_to_point[point_name]
            birth = birth_by_point[arrangement_id]
            definition_births.append(birth)
            definition_uses[point_name] += 1
            if birth >= e_move:
                all_definitions_causal = False
        transitions.append(
            {
                "e_move": e_move,
                "drawable": entry["id"],
                "kind": entry["op"],
                "definition_points": definition,
                "definition_point_birth_e_moves": definition_births,
                "marginal_cost_e": 1,
                "free_points_born": free_points_by_e[e_move],
                "explicit_bindings": explicit_by_e[e_move],
                "algebraic_representations_born": sorted(
                    representation_by_e[e_move]
                ),
            }
        )
    if not all_definitions_causal:
        raise ValueError("存在使用尚未出生点的付费步骤")

    fanout_transition = max(
        transitions,
        key=lambda transition: len(transition["free_points_born"]),
    )
    early_bindings = sum(
        birth_by_point[alias_to_point[name]] < bound_e
        for name, bound_e in explicit_binding_e.items()
    )
    reused_definition_points = [
        {"point": point, "use_count": count}
        for point, count in sorted(definition_uses.items())
        if count >= 2
    ]

    all_expression_references = set()
    for relation in relations:
        all_expression_references |= expression_symbol_ids(relation["sum"])
        all_expression_references |= expression_symbol_ids(relation["product"])
    for symbol in symbols:
        if "expression" in symbol:
            all_expression_references |= expression_symbol_ids(symbol["expression"])
    if not all_expression_references <= symbol_ids:
        raise ValueError("GA-IR 中仍有未解析的表达式符号")

    baseline_macros = _baseline_macro_partition(
        transitions,
        representations,
        symbol_ids,
    )

    charts = [
        {
            "id": "encoding-circle-phi",
            "carrier": "point on paid circle c",
            "formula": "x/(y+1)",
            "domain": "c and y != -1",
        },
        {
            "id": "baseline-x",
            "carrier": "point on paid line b",
            "formula": "x",
            "domain": "b",
        },
        {
            "id": "vertical-axis-y",
            "carrier": "point on paid line a",
            "formula": "y",
            "domain": "a",
        },
        {
            "id": "vertical-carrier-x",
            "carrier": "vertical line or radical axis",
            "formula": "constant x coordinate",
            "domain": "line with nonzero x coefficient and zero y coefficient",
        },
    ]

    return {
        "schema": "euclid-min-geometry-algebra-ir/v1",
        "source": source,
        "model": {
            "state": "available_points + available_drawables + algebraic_representations",
            "paid_transition": "add_one_new_distinct_line_or_circle_defined_by_available_points",
            "free_closure": "add_all_finite_real_intersections_of_available_drawables",
            "persistence": "monotone_no_erasure",
            "geometry_identity": "exact_geometric_equality_not_definition_syntax",
            "contextual_cost": "number_of_distinct_paid_drawables_added_to_input_state",
        },
        "charts": charts,
        "symbols": symbols,
        "algebraic_relations": relations,
        "representations": representations,
        "transitions": transitions,
        "baseline_macro_partition": baseline_macros,
        "cost_audit": {
            "construction_cost_e": 69,
            "distinct_paid_drawables": 69,
            "lines": sum(entry["op"] == "line" for entry in paid_entries),
            "circles": sum(entry["op"] == "circle" for entry in paid_entries),
            "initial_points": 2,
            "full_closure_points": len(full_report["arrangement"]["points"]),
            "free_points_born_after_paid_transitions": sum(
                len(points) for points in free_points_by_e.values()
            ),
            "explicit_free_bindings": len(explicit_binding_e),
            "named_bindings_available_earlier": early_bindings,
            "definition_point_references": sum(definition_uses.values()),
            "distinct_definition_points": len(definition_uses),
            "reused_definition_points": reused_definition_points,
            "max_free_point_fanout": {
                "e_move": fanout_transition["e_move"],
                "drawable": fanout_transition["drawable"],
                "point_count": len(fanout_transition["free_points_born"]),
            },
        },
        "consistency": {
            "all_expression_symbol_references_resolved": True,
            "all_quadratic_relations_exact": True,
            "all_representations_exact": True,
            "all_draw_definitions_causally_available": True,
            "all_named_bindings_not_later_than_declared_use": True,
            "target_bridge": {
                "source_symbol": "period.g0",
                "carrier": "radical_axis(target_transfer,c0)",
                "exact_claim": "x = g0 = 2*cos(2*pi/257)",
                "verified": True,
            },
        },
        "limitations": [
            "这是现有 69E 构造的可执行基线 IR，不声称 69E 全局最优。",
            "免费闭包出生表覆盖现有 70 个对象；加入新对象时必须动态扩展交点闭包。",
            "二次根对关系已精确验证，但根的几何分支选择仍必须由具体 gadget 证明。",
            "当前没有给任何孤立代数运算指定脱离几何状态的固定 E 单价。",
        ],
    }
