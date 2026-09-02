"""把已验证的正十七边形 19E 证书编译为几何—代数统一 IR。"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from euclid_min.geometry import Point
from euclid_min.geometry_algebra_ir import (
    add,
    drawable_record_payload,
    evaluate_expression,
    expression_symbol_ids,
    multiply,
    point_record_payload,
    rational,
    replay_full_closure,
    symbol,
)
from euclid_min.intersections import intersect
from euclid_min.replay import ProgramReplayer
from euclid_min.search.dependencies import audit_first_target_ancestry
from euclid_min.target import TargetName, adjacent_targets


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CERTIFICATE_PATH = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)
OUTPUT_PATH = CERTIFICATE_PATH.with_name("geometry-algebra-ir.json")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _other_intersection(first, second, known: Point) -> Point:
    points = intersect(first, second).points
    others = [point for point in points if point != known]
    if len(others) != 1:
        raise ValueError("无法唯一识别二次根的免费共轭点")
    return others[0]


def _algebra_system(full) -> tuple[list[dict], list[dict], dict[str, object]]:
    """从完整闭包读取四层二次塔，并逐式精确核对。"""

    names = full.names
    m0_2 = names["M0_2"]
    m1_2 = names["M1_2"]
    h0_4 = names["H0_4"]
    h1_4 = names["H1_4"]
    h4_8 = names["H4_8"]
    if not all(
        isinstance(point, Point)
        for point in (m0_2, m1_2, h0_4, h1_4, h4_8)
    ):
        raise TypeError("代数载体必须是点")

    h2_4 = _other_intersection(
        names["c_M0_2_Ay"], names["x_axis"], h0_4
    )
    h3_4 = _other_intersection(
        names["c_M1_2_Ay"], names["x_axis"], h1_4
    )
    h0_8 = _other_intersection(
        names["c_M0_4_Ay"], names["x_axis"], h4_8
    )

    values = {
        "period.eta0_2_half": m0_2.x,
        "period.eta1_2_half": m1_2.x,
        "period.eta0_2": 2 * m0_2.x,
        "period.eta1_2": 2 * m1_2.x,
        "period.eta0_4": h0_4.x,
        "period.eta2_4": h2_4.x,
        "period.eta1_4": h1_4.x,
        "period.eta3_4": h3_4.x,
        "period.eta0_8": h0_8.x,
        "period.eta4_8": h4_8.x,
    }
    descriptions = {
        "period.eta0_2_half": "半尺度周期 eta_0,2/2",
        "period.eta1_2_half": "半尺度周期 eta_1,2/2",
        "period.eta0_2": "周期 eta_0,2",
        "period.eta1_2": "周期 eta_1,2",
        "period.eta0_4": "周期 eta_0,4",
        "period.eta2_4": "eta_0,4 同一 Carlyle 圆免费产生的兄弟根 eta_2,4",
        "period.eta1_4": "周期 eta_1,4",
        "period.eta3_4": "eta_1,4 同一 Carlyle 圆免费产生的兄弟根 eta_3,4",
        "period.eta0_8": "目标迹 2*cos(2*pi/17)",
        "period.eta4_8": "当前 19E 目标桥使用的兄弟根 eta_4,8",
    }
    symbols = [
        {
            "id": symbol_id,
            "kind": (
                "derived"
                if symbol_id in {"period.eta0_2", "period.eta1_2"}
                else "quadratic_root"
            ),
            "description": descriptions[symbol_id],
        }
        for symbol_id in values
    ]

    relations = [
        {
            "id": "relation.eta2-half",
            "kind": "quadratic_root_pair",
            "roots": ["period.eta0_2_half", "period.eta1_2_half"],
            "sum": rational(-1, 2),
            "product": rational(-1),
        },
        {
            "id": "relation.scale-eta0-2",
            "kind": "definition",
            "output": "period.eta0_2",
            "expression": multiply(2, "period.eta0_2_half"),
        },
        {
            "id": "relation.scale-eta1-2",
            "kind": "definition",
            "output": "period.eta1_2",
            "expression": multiply(2, "period.eta1_2_half"),
        },
        {
            "id": "relation.eta4-even",
            "kind": "quadratic_root_pair",
            "roots": ["period.eta0_4", "period.eta2_4"],
            "sum": symbol("period.eta0_2"),
            "product": rational(-1),
        },
        {
            "id": "relation.eta4-odd",
            "kind": "quadratic_root_pair",
            "roots": ["period.eta1_4", "period.eta3_4"],
            "sum": symbol("period.eta1_2"),
            "product": rational(-1),
        },
        {
            "id": "relation.eta8-target-pair",
            "kind": "quadratic_root_pair",
            "roots": ["period.eta0_8", "period.eta4_8"],
            "sum": symbol("period.eta0_4"),
            "product": symbol("period.eta1_4"),
        },
    ]

    produced: set[str] = set()
    for relation in relations:
        if relation["kind"] == "quadratic_root_pair":
            left, right = relation["roots"]
            if values[left] + values[right] != evaluate_expression(
                relation["sum"], values
            ):
                raise ValueError(f"{relation['id']} 的根和不成立")
            if values[left] * values[right] != evaluate_expression(
                relation["product"], values
            ):
                raise ValueError(f"{relation['id']} 的根积不成立")
            produced.update(relation["roots"])
        else:
            output = relation["output"]
            if values[output] != evaluate_expression(
                relation["expression"], values
            ):
                raise ValueError(f"{relation['id']} 的定义式不成立")
            produced.add(output)
        relation["verified"] = True

    if produced != set(values):
        raise ValueError("代数关系没有恰好定义全部符号")
    target = adjacent_targets()[TargetName.B_PLUS]
    if values["period.eta0_8"] != 2 * target.x:
        raise ValueError("eta_0,8 没有精确等于目标横坐标的两倍")
    return symbols, relations, values


def _relation_inputs(relation: dict) -> set[str]:
    if relation["kind"] == "quadratic_root_pair":
        return expression_symbol_ids(relation["sum"]) | expression_symbol_ids(
            relation["product"]
        )
    return expression_symbol_ids(relation["expression"])


def _relation_outputs(relation: dict) -> set[str]:
    if relation["kind"] == "quadratic_root_pair":
        return set(relation["roots"])
    return {relation["output"]}


def _algebraic_live_slice(relations: list[dict], root_goal: str) -> dict:
    producer = {
        output: relation
        for relation in relations
        for output in _relation_outputs(relation)
    }
    live_symbols: set[str] = set()
    active_relation_ids: set[str] = set()
    pending = [root_goal]
    while pending:
        symbol_id = pending.pop()
        if symbol_id in live_symbols:
            continue
        live_symbols.add(symbol_id)
        relation = producer.get(symbol_id)
        if relation is None:
            continue
        active_relation_ids.add(relation["id"])
        pending.extend(_relation_inputs(relation))

    active_relations = [
        relation for relation in relations if relation["id"] in active_relation_ids
    ]
    quadratic_roots = {
        root
        for relation in active_relations
        if relation["kind"] == "quadratic_root_pair"
        for root in relation["roots"]
    }
    return {
        "root_goal": root_goal,
        "active_relations": [relation["id"] for relation in active_relations],
        "live_symbols": sorted(live_symbols),
        "consumed_quadratic_roots": sorted(quadratic_roots & live_symbols),
        "free_sibling_roots": sorted(quadratic_roots - live_symbols),
        "target_relevant_free_roots": sorted(
            {"period.eta0_8"} & (quadratic_roots - live_symbols)
        ),
    }


def _representations(full, values: dict[str, object]) -> list[dict]:
    names = full.names
    h2_4 = _other_intersection(
        names["c_M0_2_Ay"], names["x_axis"], names["H0_4"]
    )
    h3_4 = _other_intersection(
        names["c_M1_2_Ay"], names["x_axis"], names["H1_4"]
    )
    h0_8 = _other_intersection(
        names["c_M0_4_Ay"], names["x_axis"], names["H4_8"]
    )
    target = adjacent_targets()[TargetName.B_PLUS]

    records: list[dict] = []

    def add_representation(
        representation_id: str,
        symbol_id: str,
        point: Point,
        chart: str,
        actual_value,
        *,
        reference: str | None = None,
    ) -> None:
        if actual_value != values[symbol_id]:
            raise ValueError(f"表示 {representation_id} 的精确值不正确")
        point_record = next(
            (record for record in full.points if record.point == point), None
        )
        if point_record is None:
            raise ValueError(f"表示 {representation_id} 的点不在闭包中")
        carrier = {"kind": "point", "point_id": point_record.point_id}
        if reference is not None:
            if full.names[reference] != point:
                raise ValueError(f"表示 {representation_id} 的别名指向错误")
            carrier["reference"] = reference
        record = {
            "id": representation_id,
            "symbol": symbol_id,
            "carrier": carrier,
            "chart": chart,
            "available_e_move": point_record.birth_e_move,
            "verification": "exact_AA_equality",
        }
        if reference in full.explicit_binding_e_moves:
            record["bound_e_move"] = full.explicit_binding_e_moves[reference]
        records.append(record)

    m0_2 = names["M0_2"]
    m1_2 = names["M1_2"]
    h0_4 = names["H0_4"]
    h1_4 = names["H1_4"]
    m0_4 = names["M0_4"]
    y_point = names["Y"]
    h4_8 = names["H4_8"]
    add_representation(
        "repr.M0_2.x",
        "period.eta0_2_half",
        m0_2,
        "x",
        m0_2.x,
        reference="M0_2",
    )
    add_representation(
        "repr.M0_2.twice-x",
        "period.eta0_2",
        m0_2,
        "2*x",
        2 * m0_2.x,
        reference="M0_2",
    )
    add_representation(
        "repr.M1_2.x",
        "period.eta1_2_half",
        m1_2,
        "x",
        m1_2.x,
        reference="M1_2",
    )
    add_representation(
        "repr.M1_2.twice-x",
        "period.eta1_2",
        m1_2,
        "2*x",
        2 * m1_2.x,
        reference="M1_2",
    )
    add_representation(
        "repr.H0_4.x",
        "period.eta0_4",
        h0_4,
        "x",
        h0_4.x,
        reference="H0_4",
    )
    add_representation(
        "repr.auto.H2_4.x",
        "period.eta2_4",
        h2_4,
        "x",
        h2_4.x,
    )
    add_representation(
        "repr.H1_4.x",
        "period.eta1_4",
        h1_4,
        "x",
        h1_4.x,
        reference="H1_4",
    )
    add_representation(
        "repr.auto.H3_4.x",
        "period.eta3_4",
        h3_4,
        "x",
        h3_4.x,
    )
    add_representation(
        "repr.Y.y-minus-one",
        "period.eta1_4",
        y_point,
        "y-1",
        y_point.y - 1,
        reference="Y",
    )
    add_representation(
        "repr.M0_4.twice-x",
        "period.eta0_4",
        m0_4,
        "2*x",
        2 * m0_4.x,
        reference="M0_4",
    )
    add_representation(
        "repr.M0_4.twice-y-minus-one",
        "period.eta1_4",
        m0_4,
        "2*y-1",
        2 * m0_4.y - 1,
        reference="M0_4",
    )
    add_representation(
        "repr.auto.H0_8.x",
        "period.eta0_8",
        h0_8,
        "x",
        h0_8.x,
    )
    add_representation(
        "repr.H4_8.x",
        "period.eta4_8",
        h4_8,
        "x",
        h4_8.x,
        reference="H4_8",
    )
    add_representation(
        "repr.target.B_plus.twice-x",
        "period.eta0_8",
        target,
        "2*x",
        2 * target.x,
    )
    return records


def _macro_partition(
    transitions: tuple[dict, ...], representations: list[dict]
) -> list[dict]:
    specifications = [
        (
            "macro.axes",
            1,
            4,
            [],
            [],
            "从 O、A 和单位圆建立横轴、纵轴及方向点。",
        ),
        (
            "macro.half-scale-bootstrap",
            5,
            9,
            [],
            [],
            "建立 -1/2、-1/4 与半尺度 Carlyle 圆所需痕迹。",
        ),
        (
            "macro.eta2-half-pair",
            10,
            10,
            [],
            ["period.eta0_2_half", "period.eta1_2_half"],
            "一只圆同时产生两个半尺度 eta_2 根。",
        ),
        (
            "macro.eta4-pairs",
            11,
            12,
            ["period.eta0_2", "period.eta1_2"],
            [
                "period.eta0_4",
                "period.eta2_4",
                "period.eta1_4",
                "period.eta3_4",
            ],
            "两只圆分别产生偶、奇两组 eta_4 根。",
        ),
        (
            "macro.locate-M0_4",
            13,
            16,
            ["period.eta0_4", "period.eta1_4"],
            ["period.eta0_4", "period.eta1_4"],
            "直接得到 Y，并用三条线定位最后一个 Carlyle 圆心。",
        ),
        (
            "macro.eta8-target-pair",
            17,
            17,
            ["period.eta0_4", "period.eta1_4"],
            ["period.eta0_8", "period.eta4_8"],
            "一只圆同时产生目标迹和当前尾部使用的兄弟根。",
        ),
        (
            "macro.target-bridge",
            18,
            19,
            ["period.eta4_8"],
            ["period.eta0_8"],
            "利用兄弟根、已有圆和一条目标线命中 B_plus。",
        ),
    ]
    result = []
    covered = []
    for macro_id, first_e, last_e, inputs, outputs, interpretation in specifications:
        selected = list(transitions[first_e - 1 : last_e])
        if [item["e_move"] for item in selected] != list(
            range(first_e, last_e + 1)
        ):
            raise ValueError(f"宏 {macro_id} 的 E 区间不连续")
        paid_drawables = [item["drawable"] for item in selected]
        covered.extend(paid_drawables)
        result.append(
            {
                "id": macro_id,
                "first_e_move": first_e,
                "last_e_move": last_e,
                "observed_charged_cost_e": sum(
                    item["charged_cost_e"] for item in selected
                ),
                "observed_contextual_new_object_cost_e": sum(
                    item["marginal_new_object_cost_e"] for item in selected
                ),
                "paid_drawables": paid_drawables,
                "input_symbols": inputs,
                "output_symbols": outputs,
                "output_representations": sorted(
                    representation["id"]
                    for representation in representations
                    if representation["symbol"] in outputs
                    and first_e
                    <= representation["available_e_move"]
                    <= last_e
                ),
                "interpretation": interpretation,
            }
        )
    if covered != [item["drawable"] for item in transitions]:
        raise ValueError("宏分区没有按顺序恰好覆盖 19 个付费对象")
    return result


def build_report(certificate: dict, *, certificate_sha256: str) -> dict:
    program = certificate["construction"]["program"]
    full = replay_full_closure(program)
    replay = ProgramReplayer().replay(program)
    if replay.e_move != 19 or replay.first_target_e_move != 19:
        raise ValueError("输入证书不是冻结的首次 19E 命中程序")
    if tuple(target.value for target in replay.targets) != ("B_plus",):
        raise ValueError("输入证书没有唯一命中 B_plus")
    if len(full.transitions) != 19:
        raise ValueError("完整闭包没有得到 19 个付费转移")
    if any(
        birth >= transition["e_move"]
        for transition in full.transitions
        for birth in transition["definition_point_birth_e_moves"]
    ):
        raise ValueError("存在尚未出生就用于定义新对象的点")

    symbols, relations, values = _algebra_system(full)
    representations = _representations(full, values)
    representations_by_symbol = {}
    for representation in representations:
        representations_by_symbol.setdefault(representation["symbol"], []).append(
            representation["id"]
        )
    for relation in relations:
        relation["materialized_representations"] = sorted(
            representation_id
            for output in _relation_outputs(relation)
            for representation_id in representations_by_symbol.get(output, [])
        )

    target = adjacent_targets()[TargetName.B_PLUS]
    target_record = next(record for record in full.points if record.point == target)
    ancestry = audit_first_target_ancestry(program)
    operation_counts = Counter(
        transition["operation"] for transition in full.transitions
    )
    algebraic_live_slice = _algebraic_live_slice(
        relations, "period.eta4_8"
    )
    return {
        "schema": "euclid-min-geometry-algebra-ir/v1",
        "problem": "regular-17-adjacent-vertex",
        "profile": certificate["profile"],
        "source": {
            "certificate": str(CERTIFICATE_PATH.relative_to(REPOSITORY_ROOT)).replace(
                "\\", "/"
            ),
            "certificate_sha256": certificate_sha256,
            "construction_sha256": certificate["integrity"][
                "construction_sha256"
            ],
        },
        "semantics": {
            "state": "monotone_points_drawables_representations",
            "charged_draw_operation_cost_e": 1,
            "intersection_binding_cost_e": 0,
            "closure": "all_finite_real_intersections_after_each_new_object",
            "contextual_cost": "number_of_distinct_new_drawables_in_context",
            "duplicate_draw_note": (
                "正式 profile 仍对重复绘制收费；本基线没有重复对象，故收费成本与"
                "上下文新增对象成本相等。"
            ),
        },
        "arrangement": {
            "drawables": [
                drawable_record_payload(record) for record in full.drawables
            ],
            "points": [point_record_payload(record) for record in full.points],
        },
        "transitions": list(full.transitions),
        "algebraic_symbols": symbols,
        "algebraic_relations": relations,
        "representations": representations,
        "baseline_macro_partition": _macro_partition(
            full.transitions, representations
        ),
        "live_slice": {
            "algebraic": algebraic_live_slice,
            "geometry": {
                "root": ancestry.roots[0],
                "paid_objects": sorted(ancestry.paid_objects),
                "live_paid_objects": sorted(
                    ancestry.paid_objects - ancestry.non_ancestor_paid_objects
                ),
                "non_ancestor_paid_objects": sorted(
                    ancestry.non_ancestor_paid_objects
                ),
                "all_paid_objects_live": ancestry.all_paid_objects_are_ancestors,
            },
        },
        "cost_audit": {
            "charged_e_move": sum(
                transition["charged_cost_e"] for transition in full.transitions
            ),
            "contextual_new_object_e_move": sum(
                transition["marginal_new_object_cost_e"]
                for transition in full.transitions
            ),
            "lines": operation_counts["line"],
            "circles": operation_counts["circle"],
            "full_closure_points": len(full.points),
            "explicit_intersection_bindings": len(
                full.explicit_binding_e_moves
            ),
            "unbound_free_closure_points": sum(
                not record.aliases for record in full.points
            ),
        },
        "consistency": {
            "all_algebraic_relations_verified": all(
                relation["verified"] for relation in relations
            ),
            "target_bridge": {
                "target": "B_plus",
                "target_point_id": target_record.point_id,
                "target_point_birth_e_move": target_record.birth_e_move,
                "eta0_8_equals_twice_target_x": values["period.eta0_8"]
                == 2 * target.x,
                "target_line_contains_target": full.names["target_line"].contains(
                    target
                ),
                "unit_circle_contains_target": full.names["unit_circle"].contains(
                    target
                ),
                "verified": True,
            },
        },
        "producer": {
            "name": "euclid-min-regular17-ga-ir-builder",
            "version": 1,
        },
    }


def load_and_build(certificate_path: Path = CERTIFICATE_PATH) -> dict:
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    return build_report(
        certificate,
        certificate_sha256=_sha256_file(certificate_path),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, default=CERTIFICATE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    report = load_and_build(args.certificate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
