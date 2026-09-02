"""为 68E 合成提取 69E 基线中真正活跃的代数与几何接口。"""

from __future__ import annotations

from dependency_graph import build_nodes, transitive_cone
from geometry_algebra_ir import expression_symbol_ids


def _ordered_subset(order: list[str], selected: set[str]) -> list[str]:
    return [item for item in order if item in selected]


def _algebraic_backward_slice(ga_ir: dict, root_goal: str) -> dict:
    symbols = ga_ir["symbols"]
    symbol_by_id = {symbol["id"]: symbol for symbol in symbols}
    if root_goal not in symbol_by_id:
        raise ValueError(f"未知合成目标符号: {root_goal}")

    relations = ga_ir["algebraic_relations"]
    producer_by_root = {}
    for relation in relations:
        for root in relation["roots"]:
            if root in producer_by_root:
                raise ValueError(f"代数根存在多个生产关系: {root}")
            producer_by_root[root] = relation

    active_symbols = {root_goal}
    active_relation_ids = set()
    pending = [root_goal]
    while pending:
        symbol_id = pending.pop()
        symbol = symbol_by_id[symbol_id]
        dependencies = set()
        if symbol_id in producer_by_root:
            relation = producer_by_root[symbol_id]
            active_relation_ids.add(relation["id"])
            dependencies |= expression_symbol_ids(relation["sum"])
            dependencies |= expression_symbol_ids(relation["product"])
        if "expression" in symbol:
            dependencies |= expression_symbol_ids(symbol["expression"])
        unknown = dependencies - symbol_by_id.keys()
        if unknown:
            raise ValueError(f"活跃切片遇到未知符号: {sorted(unknown)}")
        for dependency in dependencies - active_symbols:
            active_symbols.add(dependency)
            pending.append(dependency)

    symbol_order = [symbol["id"] for symbol in symbols]
    relation_order = [relation["id"] for relation in relations]
    root_order = [
        symbol["id"]
        for symbol in symbols
        if symbol["kind"] == "quadratic_root"
    ]
    roots_from_active_relations = {
        root
        for relation in relations
        if relation["id"] in active_relation_ids
        for root in relation["roots"]
    }
    active_roots = active_symbols & set(root_order)
    free_byproduct_roots = roots_from_active_relations - active_roots
    inactive_roots = set(root_order) - roots_from_active_relations

    relation_records = []
    for relation in relations:
        if relation["id"] not in active_relation_ids:
            continue
        demanded = [root for root in relation["roots"] if root in active_roots]
        byproducts = [
            root for root in relation["roots"] if root in free_byproduct_roots
        ]
        if not demanded:
            raise AssertionError(f"活跃关系没有被需求的根: {relation['id']}")
        relation_records.append(
            {
                "id": relation["id"],
                "demanded_roots": demanded,
                "free_sibling_byproducts": byproducts,
                "input_symbols": _ordered_subset(
                    symbol_order,
                    expression_symbol_ids(relation["sum"])
                    | expression_symbol_ids(relation["product"]),
                ),
            }
        )

    return {
        "root_goal": root_goal,
        "active_symbols": _ordered_subset(symbol_order, active_symbols),
        "active_quadratic_roots": _ordered_subset(root_order, active_roots),
        "free_sibling_byproduct_roots": _ordered_subset(
            root_order, free_byproduct_roots
        ),
        "inactive_quadratic_roots": _ordered_subset(root_order, inactive_roots),
        "active_relations": _ordered_subset(relation_order, active_relation_ids),
        "inactive_relations": _ordered_subset(
            relation_order, set(relation_order) - active_relation_ids
        ),
        "relation_liveness": relation_records,
        "summary": {
            "quadratic_roots_total": len(root_order),
            "demanded_quadratic_roots": len(active_roots),
            "free_sibling_byproduct_roots": len(free_byproduct_roots),
            "inactive_quadratic_roots": len(inactive_roots),
            "relations_total": len(relations),
            "active_relations": len(active_relation_ids),
            "inactive_relations": len(relations) - len(active_relation_ids),
        },
    }


def _macro_liveness(
    ga_ir: dict,
    active_roots: set[str],
    free_byproduct_roots: set[str],
) -> list[dict]:
    result = []
    for macro in ga_ir["baseline_macro_partition"]:
        outputs = macro["output_symbols"]
        demanded = [symbol for symbol in outputs if symbol in active_roots]
        byproducts = [
            symbol for symbol in outputs if symbol in free_byproduct_roots
        ]
        result.append(
            {
                "id": macro["id"],
                "first_e_move": macro["first_e_move"],
                "last_e_move": macro["last_e_move"],
                "observed_contextual_cost_e": macro[
                    "observed_contextual_cost_e"
                ],
                "demanded_output_symbols": demanded,
                "free_byproduct_output_symbols": byproducts,
                "classification": (
                    "algebraically_active"
                    if demanded
                    else "geometric_foundation_or_transfer"
                ),
            }
        )
    return result


def _paid_names_in_range(
    nodes: list[dict],
    active: set[str],
    first_e: int,
    last_e: int,
) -> list[str]:
    return [
        node["id"]
        for node in nodes
        if node["paid"]
        and first_e <= node["e_move"] <= last_e
        and node["id"] in active
    ]


def _geometric_slice(certificate: dict) -> dict:
    nodes = build_nodes(certificate["construction"]["program"])
    nodes_by_id = {node["id"]: node for node in nodes}
    target_active = transitive_cone(nodes_by_id, ["target_transfer"])
    target_paid = [
        node["id"] for node in nodes if node["paid"] and node["id"] in target_active
    ]

    low_active = transitive_cone(nodes_by_id, ["F0"])
    high_active = transitive_cone(nodes_by_id, ["F56"])
    low_paid = _paid_names_in_range(nodes, low_active, 47, 55)
    high_paid = _paid_names_in_range(nodes, high_active, 56, 64)
    joint_paid = _paid_names_in_range(
        nodes,
        low_active | high_active,
        47,
        64,
    )
    expected_low = [
        node["id"]
        for node in nodes
        if node["paid"] and 47 <= node["e_move"] <= 55
    ]
    expected_high = [
        node["id"]
        for node in nodes
        if node["paid"] and 56 <= node["e_move"] <= 64
    ]
    if low_paid != expected_low or high_paid != expected_high:
        raise ValueError("尾部基线存在可由声明式反向切片直接删除的对象")
    if len(target_paid) != 69:
        raise ValueError("最终对象的声明式依赖锥不再包含全部 69 个付费对象")

    return {
        "target_object": "target_transfer",
        "target_declared_dependency_paid_drawables": target_paid,
        "target_declared_dependency_paid_count": len(target_paid),
        "tail_regions": [
            {
                "id": "low-tail-47-55",
                "root_point": "F0",
                "first_e_move": 47,
                "last_e_move": 55,
                "live_paid_drawables": low_paid,
                "directly_dead_paid_drawables": [],
            },
            {
                "id": "high-tail-56-64",
                "root_point": "F56",
                "first_e_move": 56,
                "last_e_move": 64,
                "live_paid_drawables": high_paid,
                "directly_dead_paid_drawables": [],
            },
            {
                "id": "joint-tail-47-64",
                "root_point": "F0+F56",
                "first_e_move": 47,
                "last_e_move": 64,
                "live_paid_drawables": joint_paid,
                "directly_dead_paid_drawables": [],
            },
        ],
        "conclusion": (
            "活跃输出减少了，但原始尾部程序的 18 个付费对象仍全部服务于 F0 或 F56；"
            "68E 必须重编译接口，不能靠删除基线死代码得到。"
        ),
    }


def _representation_ids(ga_ir: dict, symbols: set[str]) -> list[str]:
    return [
        representation["id"]
        for representation in ga_ir["representations"]
        if representation["symbol"] in symbols
    ]


def build_synthesis_live_slice(
    certificate: dict,
    ga_ir: dict,
    gadget_library: dict,
    source: dict,
) -> dict:
    """构建面向 68E 生成式搜索的活跃接口与成功判据。"""

    algebra = _algebraic_backward_slice(ga_ir, "period.g0")
    active_roots = set(algebra["active_quadratic_roots"])
    free_byproduct_roots = set(algebra["free_sibling_byproduct_roots"])
    macro_liveness = _macro_liveness(
        ga_ir,
        active_roots,
        free_byproduct_roots,
    )
    geometry = _geometric_slice(certificate)

    gadgets = {gadget["id"]: gadget for gadget in gadget_library["gadgets"]}
    low = gadgets["gadget.low-tail-9e"]
    high = gadgets["gadget.high-tail-9e"]
    required_points = sorted(
        set(low["geometric_interface"]["required_points"])
        | set(high["geometric_interface"]["required_points"])
    )
    required_drawables = sorted(
        set(low["geometric_interface"]["required_drawables"])
        | set(high["geometric_interface"]["required_drawables"])
    )
    input_symbols = [
        *low["algebraic_interface"]["input_symbols"],
        *high["algebraic_interface"]["input_symbols"],
    ]
    if len(input_symbols) != len(set(input_symbols)):
        raise ValueError("两个尾部 gadget 的代数输入出现意外重复")

    region_relation_ids = {
        "relation.e-low-aux",
        "relation.e0",
        "relation.f0",
        "relation.e-high-aux",
        "relation.e24",
        "relation.f56",
    }
    region_roots = {
        root
        for relation in ga_ir["algebraic_relations"]
        if relation["id"] in region_relation_ids
        for root in relation["roots"]
    }
    region_active = active_roots & region_roots
    required_outputs = ["period.f0", "period.f56"]
    internal_symbols = [
        symbol
        for symbol in algebra["active_quadratic_roots"]
        if symbol in region_active and symbol not in required_outputs
    ]
    byproducts = [
        symbol
        for symbol in algebra["free_sibling_byproduct_roots"]
        if symbol in region_roots
    ]
    output_representations = _representation_ids(ga_ir, set(required_outputs))
    if output_representations != ["repr.F0", "repr.F56"]:
        raise ValueError("尾部最小输出表示不再是 F0 与 F56")

    return {
        "schema": "euclid-min-regular-257-synthesis-live-slice/v1",
        "source": source,
        "semantics": {
            "algebraic_liveness": (
                "a quadratic relation is active when at least one root is demanded; "
                "the sibling root is a free byproduct, not a required output"
            ),
            "geometric_liveness": (
                "declared certificate dependency cone, with intersections free and "
                "all traces persistent"
            ),
            "optimization_use": (
                "shrink replacement interfaces before exact stateful geometric costing"
            ),
        },
        "algebraic_slice": algebra,
        "baseline_macro_liveness": macro_liveness,
        "geometric_slice": geometry,
        "synthesis_contract": {
            "id": "contract.joint-tail-at-46e-to-68e",
            "replace_e_moves": [47, 64],
            "input_state_after_e_move": 46,
            "required_geometric_points": required_points,
            "required_geometric_drawables": required_drawables,
            "input_symbols": input_symbols,
            "input_representations": sorted(
                set(low["algebraic_interface"]["input_representations"])
                | set(high["algebraic_interface"]["input_representations"])
            ),
            "required_output_symbols": required_outputs,
            "required_output_representations": output_representations,
            "internal_demanded_symbols_not_in_output_interface": internal_symbols,
            "free_sibling_byproducts_not_in_output_interface": byproducts,
            "baseline_contextual_cost_e": 18,
            "maximum_candidate_contextual_cost_e": 17,
            "downstream_fixed_suffix_cost_e": 5,
            "resulting_total_upper_bound_e": 68,
            "success_requirements": [
                "候选从精确 46E 前缀状态出发。",
                "每个新增对象都由当时可用的两个点定义，且按几何恒等去重。",
                "每笔之后加入全部有限实交点，交点不计 E。",
                "在不超过 17 个不同新对象内精确物化 period.f0 与 period.f56。",
                "复用原 65E—69E 后缀后，目标在不晚于 68E 首次出现。",
            ],
        },
        "conclusions": [
            "当前高斯周期分解的 17 个二次关系全部活跃，不能直接删去某一整层关系。",
            "34 个二次根中只有 23 个被目标继续消费，另 11 个只是活跃关系免费带出的共轭根。",
            "联合尾部替换的外部输出只需 F0 与 F56；原先十二个宏输出不应继续作为合成器的硬约束。",
            "基线尾部 18 条直线全部在 F0/F56 的声明式依赖锥中，因此目标是重新合成至多 17E，而不是删死代码。",
        ],
        "limitations": [
            "活跃切片只缩小必要接口，不证明 17E 联合尾部一定存在。",
            "代数常数在关系式中作为字面量出现；其现实几何载体仍属于 46E 前缀状态。",
            "几何活跃性沿基线声明绑定计算；替代程序仍须通过精确重放与完整免费闭包验证。",
        ],
    }
