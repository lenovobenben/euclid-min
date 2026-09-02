"""几何—代数 IR 的表达式与完整闭包调度基础设施。

这一模块不为抽象代数运算规定固定 E 单价。它只负责两件事：

1. 把一份声明式尺规程序按正式语义重放为逐笔付费转移，并显式物化每笔新对象
   带来的全部免费有限实交点；
2. 提供可执行的代数表达式树，使具体问题的生成器能够在 Sage 精确数域中核对
   根和、根积及几何载体。

问题专属的符号、二次关系和目标桥接由实验生成器提供；这里保持为可复用内核。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sage.all import AA, QQ

from .geometry import Circle, Drawable, Line, Point
from .intersections import IntersectionKind, intersect
from .state import GeometryState


INITIAL_NAMES = ("O", "A", "unit_circle")


def rational(numerator: int, denominator: int = 1) -> dict:
    """返回规范的有理常数表达式。"""

    value = QQ(numerator) / QQ(denominator)
    return {
        "op": "rational",
        "numerator": int(value.numerator()),
        "denominator": int(value.denominator()),
    }


def symbol(symbol_id: str) -> dict:
    return {"op": "symbol", "id": symbol_id}


def expression(value: dict | int | str) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, int):
        return rational(value)
    if isinstance(value, str):
        return symbol(value)
    raise TypeError(f"不支持的 GA-IR 表达式节点 {value!r}")


def add(*args: dict | int | str) -> dict:
    return {"op": "add", "args": [expression(arg) for arg in args]}


def multiply(*args: dict | int | str) -> dict:
    return {"op": "mul", "args": [expression(arg) for arg in args]}


def negate(arg: dict | int | str) -> dict:
    return {"op": "neg", "arg": expression(arg)}


def subtract(left: dict | int | str, right: dict | int | str) -> dict:
    return add(left, negate(right))


def divide(
    numerator: dict | int | str,
    denominator: dict | int | str,
) -> dict:
    return {
        "op": "div",
        "numerator": expression(numerator),
        "denominator": expression(denominator),
    }


def expression_symbol_ids(node: dict) -> set[str]:
    """返回表达式直接或递归引用的全部符号 ID。"""

    operation = node["op"]
    if operation == "rational":
        return set()
    if operation == "symbol":
        return {node["id"]}
    if operation in {"add", "mul"}:
        return set().union(
            *(expression_symbol_ids(arg) for arg in node["args"])
        )
    if operation == "neg":
        return expression_symbol_ids(node["arg"])
    if operation == "div":
        return expression_symbol_ids(node["numerator"]) | expression_symbol_ids(
            node["denominator"]
        )
    raise ValueError(f"未知 GA-IR 表达式操作 {operation!r}")


def evaluate_expression(node: dict, values: dict[str, Any]):
    """在 ``AA`` 中精确求值一棵 GA-IR 表达式树。"""

    operation = node["op"]
    if operation == "rational":
        denominator = node["denominator"]
        if denominator <= 0:
            raise ValueError("GA-IR 有理数分母必须为正")
        return AA(QQ(node["numerator"]) / QQ(denominator))
    if operation == "symbol":
        try:
            return AA(values[node["id"]])
        except KeyError as error:
            raise ValueError(f"GA-IR 表达式引用未知符号 {node['id']!r}") from error
    if operation == "add":
        return sum(
            (evaluate_expression(arg, values) for arg in node["args"]),
            AA(0),
        )
    if operation == "mul":
        result = AA(1)
        for arg in node["args"]:
            result *= evaluate_expression(arg, values)
        return result
    if operation == "neg":
        return -evaluate_expression(node["arg"], values)
    if operation == "div":
        denominator = evaluate_expression(node["denominator"], values)
        if denominator == 0:
            raise ZeroDivisionError("GA-IR 表达式出现零分母")
        return evaluate_expression(node["numerator"], values) / denominator
    raise ValueError(f"未知 GA-IR 表达式操作 {operation!r}")


@dataclass(frozen=True, slots=True)
class ClosurePoint:
    """一个完整闭包点及其最早出现时刻。"""

    point_id: str
    point: Point
    birth_e_move: int
    aliases: tuple[str, ...]
    incident_drawables: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClosureDrawable:
    """一个免费初始对象或计费绘制对象。"""

    drawable_id: str
    drawable: Drawable
    operation: str
    birth_e_move: int


@dataclass(frozen=True, slots=True)
class FullClosureReplay:
    """声明式程序的完整显式闭包重放结果。"""

    state: GeometryState
    names: dict[str, Point | Drawable]
    points: tuple[ClosurePoint, ...]
    drawables: tuple[ClosureDrawable, ...]
    transitions: tuple[dict, ...]
    explicit_binding_e_moves: dict[str, int]

    def point_record(self, reference: str) -> ClosurePoint:
        value = self.names[reference]
        if not isinstance(value, Point):
            raise TypeError(f"{reference!r} 不是点")
        for record in self.points:
            if record.point == value:
                return record
        raise KeyError(reference)

    def point_id(self, point: Point) -> str:
        for record in self.points:
            if record.point == point:
                return record.point_id
        raise KeyError("点不在完整闭包中")


def _direct_definition(entry: dict) -> tuple[str, str]:
    if entry["op"] == "line":
        return tuple(entry["through"])
    if entry["op"] == "circle":
        return (entry["center"], entry["through"])
    raise ValueError(f"{entry['op']!r} 不是付费绘制操作")


def _find_equal_point_index(records: list[dict], point: Point) -> int | None:
    for index, record in enumerate(records):
        if record["point"] == point:
            return index
    return None


def replay_full_closure(program: list[dict]) -> FullClosureReplay:
    """显式重放全部有限实交点并导出逐 E 转移。

    与 verifier 的惰性闭包不同，这个入口会在每次加入新对象后物化它和全部既有
    对象的有限实交点。显式 ``intersect`` 条目只负责给已经存在的点绑定别名，
    因而可以审计“实际出生 E 步”和“证书文本绑定 E 步”的差异。
    """

    state = GeometryState.fixed_initial()
    origin, start = state.points
    unit_circle = state.circles[0]
    names: dict[str, Point | Drawable] = {
        "O": origin,
        "A": start,
        "unit_circle": unit_circle,
    }
    point_records: list[dict] = [
        {
            "point_id": "point.O",
            "point": origin,
            "birth_e_move": 0,
            "aliases": ["O"],
        },
        {
            "point_id": "point.A",
            "point": start,
            "birth_e_move": 0,
            "aliases": ["A"],
        },
    ]
    drawables = [
        ClosureDrawable("unit_circle", unit_circle, "initial_circle", 0)
    ]
    transitions: list[dict] = []
    explicit_by_e: dict[int, list[str]] = {}
    explicit_binding_e_moves: dict[str, int] = {}
    e_move = 0

    for program_index, entry in enumerate(program):
        entry_id = entry["id"]
        if entry_id in names:
            raise ValueError(f"程序 ID 重复 {entry_id!r}")
        operation = entry["op"]
        if operation == "intersect":
            first = names[entry["objects"][0]]
            second = names[entry["objects"][1]]
            if not isinstance(first, (Line, Circle)) or not isinstance(
                second, (Line, Circle)
            ):
                raise TypeError(f"交点 {entry_id!r} 的父项不是几何对象")
            result = intersect(first, second)
            if result.kind == IntersectionKind.COINCIDENT:
                raise ValueError(f"交点 {entry_id!r} 的两个父对象重合")
            index = entry["index"]
            if index >= len(result.points):
                raise ValueError(f"交点 {entry_id!r} 的索引越界")
            point = result.points[index]
            point_index = _find_equal_point_index(point_records, point)
            if point_index is None:
                raise RuntimeError(
                    f"交点 {entry_id!r} 尚未由自动完整闭包产生"
                )
            names[entry_id] = point_records[point_index]["point"]
            aliases = point_records[point_index]["aliases"]
            if entry_id not in aliases:
                aliases.append(entry_id)
            explicit_by_e.setdefault(e_move, []).append(entry_id)
            explicit_binding_e_moves[entry_id] = e_move
            continue

        if operation not in {"line", "circle"}:
            raise ValueError(f"不支持的程序操作 {operation!r}")
        first_reference, second_reference = _direct_definition(entry)
        first = names[first_reference]
        second = names[second_reference]
        if not isinstance(first, Point) or not isinstance(second, Point):
            raise TypeError(f"绘制对象 {entry_id!r} 的定义项不是点")

        e_move += 1
        if operation == "line":
            addition = state.draw_line(first, second)
        else:
            addition = state.draw_circle(first, second)
        names[entry_id] = addition.object
        drawables.append(
            ClosureDrawable(entry_id, addition.object, operation, e_move)
        )

        free_points_born: list[str] = []
        for ordinal, point in enumerate(sorted(addition.new_points), start=1):
            if _find_equal_point_index(point_records, point) is not None:
                raise RuntimeError("GeometryState 把已有点报告为新点")
            point_id = f"point.e{e_move:02d}.{ordinal:03d}"
            point_records.append(
                {
                    "point_id": point_id,
                    "point": point,
                    "birth_e_move": e_move,
                    "aliases": [],
                }
            )
            free_points_born.append(point_id)

        first_record = point_records[_find_equal_point_index(point_records, first)]
        second_record = point_records[_find_equal_point_index(point_records, second)]
        transitions.append(
            {
                "e_move": e_move,
                "program_index": program_index,
                "drawable": entry_id,
                "operation": operation,
                "definition_references": [first_reference, second_reference],
                "definition_point_ids": [
                    first_record["point_id"],
                    second_record["point_id"],
                ],
                "definition_point_birth_e_moves": [
                    first_record["birth_e_move"],
                    second_record["birth_e_move"],
                ],
                "charged_cost_e": 1,
                "marginal_new_object_cost_e": int(addition.new_object),
                "free_points_born": free_points_born,
                "explicit_bindings_after_draw": [],
            }
        )

    for transition in transitions:
        transition["explicit_bindings_after_draw"] = explicit_by_e.get(
            transition["e_move"], []
        )

    completed_points: list[ClosurePoint] = []
    for record in point_records:
        point = record["point"]
        incident = tuple(
            drawable.drawable_id
            for drawable in drawables
            if drawable.drawable.contains(point)
        )
        if record["birth_e_move"] > 0:
            incident_births = sorted(
                {
                    drawable.birth_e_move
                    for drawable in drawables
                    if drawable.drawable_id in incident
                }
            )
            if len(incident_births) < 2:
                raise RuntimeError(
                    f"闭包点 {record['point_id']} 少于两个不同对象支撑"
                )
            if incident_births[1] != record["birth_e_move"]:
                raise RuntimeError(
                    f"闭包点 {record['point_id']} 的出生时刻审计不一致"
                )
        completed_points.append(
            ClosurePoint(
                point_id=record["point_id"],
                point=point,
                birth_e_move=record["birth_e_move"],
                aliases=tuple(record["aliases"]),
                incident_drawables=incident,
            )
        )

    return FullClosureReplay(
        state=state,
        names=names,
        points=tuple(completed_points),
        drawables=tuple(drawables),
        transitions=tuple(transitions),
        explicit_binding_e_moves=explicit_binding_e_moves,
    )


def point_record_payload(record: ClosurePoint) -> dict:
    """返回不依赖 Sage 内部 AA 序列化的稳定点记录。"""

    return {
        "id": record.point_id,
        "birth_e_move": record.birth_e_move,
        "aliases": list(record.aliases),
        "incident_drawables": list(record.incident_drawables),
    }


def drawable_record_payload(record: ClosureDrawable) -> dict:
    return {
        "id": record.drawable_id,
        "operation": record.operation,
        "birth_e_move": record.birth_e_move,
    }


def paid_entry_ids(program: Iterable[dict]) -> tuple[str, ...]:
    return tuple(
        entry["id"]
        for entry in program
        if entry["op"] in {"line", "circle"}
    )
