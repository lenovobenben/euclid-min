"""把编码圆上的二次根对编译成可验证的根载线任务。"""

from __future__ import annotations

from cyclotomic_replay import Line, ORDER_FIELD, Point
from geometry_algebra_ir import _algebra_system, evaluate_expression
from semantic_dependency import exact_replay_universe


TAIL_RELATION_CARRIERS = (
    ("relation.e0", "low", "H2Y1"),
    ("relation.e-low-aux", "low", "AJ2"),
    ("relation.f0", "low", "L2I2"),
    ("relation.e24", "high", "M2O2"),
    ("relation.e-high-aux", "high", "AQ2"),
    ("relation.f56", "high", "S2P2"),
)


def _const(value: int) -> dict:
    return {"op": "const", "value": value}


def _add(*args: dict) -> dict:
    return {"op": "add", "args": list(args)}


def _neg(arg: dict) -> dict:
    return {"op": "neg", "arg": arg}


def _div(numerator: dict, denominator: dict) -> dict:
    return {
        "op": "div",
        "numerator": numerator,
        "denominator": denominator,
    }


def _available_prefix_point_ids(ga_ir: dict, cutoff_e: int) -> set[str]:
    result = {"B", "C"}
    for transition in ga_ir["transitions"]:
        if transition["e_move"] > cutoff_e:
            break
        result.update(transition["free_points_born"])
    return result


def _paid_entry_by_id(certificate: dict) -> dict[str, dict]:
    return {
        entry["id"]: entry
        for entry in certificate["construction"]["program"]
        if entry["op"] != "intersect"
    }


def build_tail_quadratic_chord_ir(
    certificate: dict,
    ga_ir: dict,
    full_report: dict,
    live_slice: dict,
    source: dict,
) -> dict:
    """编译六个尾部二次关系，并核对公式载线与 69E 基线完全相同。"""

    _symbols, exact_relations, values = _algebra_system()
    exact_relation_by_id = {
        relation["id"]: relation for relation in exact_relations
    }
    serialized_relation_by_id = {
        relation["id"]: relation for relation in ga_ir["algebraic_relations"]
    }
    demanded_roots = set(
        live_slice["algebraic_slice"]["active_quadratic_roots"]
    )
    byproduct_roots = set(
        live_slice["algebraic_slice"]["free_sibling_byproduct_roots"]
    )
    replay = exact_replay_universe(certificate)
    names = replay["replayer"].names
    paid_entries = _paid_entry_by_id(certificate)
    transition_by_drawable = {
        transition["drawable"]: transition for transition in ga_ir["transitions"]
    }
    prefix_points = _available_prefix_point_ids(ga_ir, 46)
    arrangement_points = full_report["arrangement"]["points"]

    tasks = []
    for relation_id, branch, carrier_name in TAIL_RELATION_CARRIERS:
        relation = serialized_relation_by_id[relation_id]
        exact_relation = exact_relation_by_id[relation_id]
        root_sum = relation["sum"]
        root_product = relation["product"]
        sum_value = evaluate_expression(root_sum, values)
        product_value = evaluate_expression(root_product, values)
        if sum_value == 0:
            raise ValueError(f"{relation_id} 的根和为零，不能使用冻结的 b 轴截点公式")
        if product_value == 1:
            raise ValueError(f"{relation_id} 的根积为一，不能使用冻结的 a 轴截点公式")

        # 对编码点 phi(t)=(2t/(t^2+1),(1-t^2)/(t^2+1))，
        # 根 t1,t2 的弦线恒为 -s*x+(p-1)*y+(p+1)=0。
        compiled_line = Line(
            -sum_value,
            product_value - 1,
            product_value + 1,
        )
        baseline_line = names[carrier_name]
        if not isinstance(baseline_line, Line) or compiled_line != baseline_line:
            raise ValueError(f"{relation_id} 的公式载线与基线 {carrier_name} 不一致")
        for root in exact_relation["roots"]:
            value = values[root]
            denominator = value * value + 1
            point_x = 2 * value / denominator
            point_y = (1 - value * value) / denominator
            if not compiled_line.contains(Point(point_x, point_y)):
                raise ValueError(f"{relation_id} 的根 {root} 不在公式载线上")

        available_incident_points = [
            point["id"]
            for point in arrangement_points
            if point["id"] in prefix_points
            and carrier_name in point["incident_drawables"]
        ]
        demanded = [root for root in relation["roots"] if root in demanded_roots]
        byproducts = [
            root for root in relation["roots"] if root in byproduct_roots
        ]
        if len(demanded) != 1 or len(byproducts) != 1:
            raise ValueError(f"{relation_id} 没有恰好一个需求根和一个免费兄弟根")
        entry = paid_entries[carrier_name]
        if entry["op"] != "line":
            raise ValueError(f"二次根载体 {carrier_name} 不是直线")

        x_on_b = _div(_const(2), root_sum)
        y_on_a = _div(
            _add(root_product, _const(1)),
            _add(_const(1), _neg(root_product)),
        )
        if evaluate_expression(x_on_b, values) != ORDER_FIELD(2) / sum_value:
            raise AssertionError("b 轴截点表达式核对失败")
        if evaluate_expression(y_on_a, values) != (
            product_value + 1
        ) / (1 - product_value):
            raise AssertionError("a 轴截点表达式核对失败")

        tasks.append(
            {
                "id": f"chord-task.{relation_id.removeprefix('relation.')}",
                "branch": branch,
                "relation": relation_id,
                "demanded_root": demanded[0],
                "free_sibling_byproduct": byproducts[0],
                "root_sum": root_sum,
                "root_product": root_product,
                "compiled_line_coefficients": {
                    "x": _neg(root_sum),
                    "y": _add(root_product, _const(-1)),
                    "constant": _add(root_product, _const(1)),
                },
                "canonical_definition_points": {
                    "on_baseline_b": {
                        "chart": "baseline-x",
                        "value": x_on_b,
                    },
                    "on_axis_a": {
                        "chart": "vertical-axis-y",
                        "value": y_on_a,
                    },
                },
                "baseline_carrier": carrier_name,
                "baseline_carrier_e_move": transition_by_drawable[carrier_name][
                    "e_move"
                ],
                "baseline_definition_points": list(entry["through"]),
                "available_incident_points_at_46e": available_incident_points,
                "available_incident_point_count_at_46e": len(
                    available_incident_points
                ),
                "verification": {
                    "formula_line_equals_baseline_carrier": True,
                    "both_exact_roots_on_formula_line": True,
                    "intercept_expressions_exact": True,
                },
            }
        )

    points_with_incidence = sorted(
        {
            point
            for task in tasks
            for point in task["available_incident_points_at_46e"]
        }
    )
    tasks_with_two_prefix_points = [
        task["id"]
        for task in tasks
        if task["available_incident_point_count_at_46e"] >= 2
    ]
    if points_with_incidence != ["A"] or tasks_with_two_prefix_points:
        raise ValueError("六条尾部载线的 46E 前缀关联结论发生变化")

    return {
        "schema": "euclid-min-regular-257-tail-quadratic-chord-ir/v1",
        "source": source,
        "encoding": {
            "chart": "encoding-circle-phi",
            "point_formula": "phi(t)=(2t/(t^2+1),(1-t^2)/(t^2+1))",
            "quadratic": "t^2-s*t+p=0",
            "root_chord": "-s*x+(p-1)*y+(p+1)=0",
            "baseline_b_intercept": "(2/s,-1)",
            "axis_a_intercept": "(0,(p+1)/(1-p))",
            "verified_symbolically_and_in_cyclotomic_field": True,
        },
        "tasks": tasks,
        "summary": {
            "tail_relation_tasks": len(tasks),
            "formula_lines_equal_baseline_carriers": sum(
                task["verification"]["formula_line_equals_baseline_carrier"]
                for task in tasks
            ),
            "tasks_with_any_available_incident_point_at_46e": sum(
                bool(task["available_incident_points_at_46e"])
                for task in tasks
            ),
            "tasks_with_two_available_incident_points_at_46e": len(
                tasks_with_two_prefix_points
            ),
            "distinct_available_incident_points_at_46e": points_with_incidence,
        },
        "compiler_contract": {
            "inputs": ["root_sum", "root_product", "exact_46e_geometry_state"],
            "output": "one_exact_root_chord_line_and_both_free_root_intersections",
            "cost_rule": (
                "count only distinct new construction lines/circles needed to materialize "
                "two definition points and the chord in the current state"
            ),
            "search_focus": [
                "为六条载线生成基线轴截点以外的等价定位点表示。",
                "让一条新增对象同时产生两条不同载线所需的定位点。",
                "对候选定位点执行完整免费交点闭包和精确几何去重。",
            ],
        },
        "conclusions": [
            "二次方程的根和、根积已经被编译为真实载线，而不是抽象固定 E 单价。",
            "46E 前缀在 AJ2、AQ2 上各已有同一个点 A，其余四条载线没有前缀点。",
            "没有任何尾部根载线在 46E 时已有两个定位点，所以不能直接以 1E 画出并省步。",
            "下一步应搜索共享定位点生产程序，而不是再次枚举六条载线本身。",
        ],
        "limitations": [
            "这里核对的是当前六组二次关系；等价代数改写可能产生不同根和、根积与载线。",
            "前缀关联结论不排除一条新对象同时解锁多个后续定位点。",
        ],
    }
