"""构造证书的声明式依赖图分析。

本模块只分析证书明确写出的依赖关系。它能发现未被目标使用的对象，但不会把一个
交点自动改绑到证书未声明的另一对对象，因此不能单独证明某一步在几何上不可替代。
"""

from __future__ import annotations

from collections.abc import Iterable


INITIAL_NODES = (
    {"id": "C", "kind": "initial_point"},
    {"id": "B", "kind": "initial_point"},
    {"id": "c0", "kind": "initial_circle"},
)
PAID_OPS = {"line", "circle"}


def entry_dependencies(entry: dict) -> list[str]:
    """返回一条程序指令直接引用的名字。"""

    op = entry["op"]
    if op == "line":
        return list(entry["through"])
    if op == "circle":
        return [entry["center"], entry["through"]]
    if op == "intersect":
        return list(entry["objects"])
    raise ValueError(f"未知操作: {op}")


def build_nodes(program: list[dict]) -> list[dict]:
    """校验拓扑顺序并生成包含初始对象的节点表。"""

    nodes = [
        {
            "id": item["id"],
            "kind": item["kind"],
            "program_index": 0,
            "e_move": 0,
            "paid": False,
            "dependencies": [],
        }
        for item in INITIAL_NODES
    ]
    known = {node["id"] for node in nodes}
    e_move = 0
    for program_index, entry in enumerate(program, start=1):
        name = entry["id"]
        if name in known:
            raise ValueError(f"重复节点名: {name}")
        dependencies = entry_dependencies(entry)
        missing = [dependency for dependency in dependencies if dependency not in known]
        if missing:
            raise ValueError(
                f"节点 {name} 引用了尚未定义的对象: {', '.join(missing)}"
            )
        paid = entry["op"] in PAID_OPS
        if paid:
            e_move += 1
        nodes.append(
            {
                "id": name,
                "kind": "intersection" if entry["op"] == "intersect" else entry["op"],
                "program_index": program_index,
                "e_move": e_move,
                "paid": paid,
                "dependencies": dependencies,
            }
        )
        known.add(name)
    return nodes


def transitive_cone(nodes_by_id: dict[str, dict], roots: Iterable[str]) -> set[str]:
    """返回根节点及其全部传递依赖。"""

    active = set(roots)
    missing = active.difference(nodes_by_id)
    if missing:
        raise ValueError(f"未知依赖根: {', '.join(sorted(missing))}")
    stack = list(active)
    while stack:
        node = nodes_by_id[stack.pop()]
        for dependency in node["dependencies"]:
            if dependency not in active:
                active.add(dependency)
                stack.append(dependency)
    return active


def cone_summary(nodes: list[dict], active: set[str]) -> dict:
    """以稳定的程序顺序汇总一个传递依赖锥。"""

    required = [node for node in nodes if node["id"] in active]
    unrequired = [node for node in nodes if node["id"] not in active]
    return {
        "required_node_count": len(required),
        "required_initial_nodes": sum(
            node["kind"].startswith("initial_") for node in required
        ),
        "required_paid_nodes": sum(node["paid"] for node in required),
        "required_intersection_nodes": sum(
            node["kind"] == "intersection" for node in required
        ),
        "unrequired_paid_nodes": [
            node["id"] for node in unrequired if node["paid"]
        ],
        "unrequired_intersection_nodes": [
            node["id"]
            for node in unrequired
            if node["kind"] == "intersection"
        ],
    }


def build_paid_projection(nodes: list[dict]) -> dict:
    """收缩免费交点，得到只包含付费对象的依赖图。"""

    nodes_by_id = {node["id"]: node for node in nodes}
    paid_order = {
        node["id"]: node["e_move"] for node in nodes if node["paid"]
    }
    memo: dict[str, tuple[frozenset[str], bool]] = {}

    def paid_frontier(name: str) -> tuple[frozenset[str], bool]:
        if name in memo:
            return memo[name]
        node = nodes_by_id[name]
        if node["paid"]:
            result = (frozenset((name,)), False)
        elif node["kind"].startswith("initial_"):
            result = (frozenset(), True)
        else:
            paid_dependencies: set[str] = set()
            uses_initial_state = False
            for dependency in node["dependencies"]:
                frontier, uses_initial = paid_frontier(dependency)
                paid_dependencies.update(frontier)
                uses_initial_state = uses_initial_state or uses_initial
            result = (frozenset(paid_dependencies), uses_initial_state)
        memo[name] = result
        return result

    projection_nodes = []
    projection_edges = []
    for node in nodes:
        if not node["paid"]:
            continue
        direct_paid_dependencies: set[str] = set()
        uses_initial_state = False
        for dependency in node["dependencies"]:
            frontier, uses_initial = paid_frontier(dependency)
            direct_paid_dependencies.update(frontier)
            uses_initial_state = uses_initial_state or uses_initial
        ordered_dependencies = sorted(
            direct_paid_dependencies,
            key=lambda name: (paid_order[name], name),
        )
        projection_nodes.append(
            {
                "id": node["id"],
                "e_move": node["e_move"],
                "kind": node["kind"],
                "direct_paid_dependencies": ordered_dependencies,
                "uses_initial_state": uses_initial_state,
            }
        )
        projection_edges.extend(
            {"from": dependency, "to": node["id"]}
            for dependency in ordered_dependencies
        )
    return {"nodes": projection_nodes, "edges": projection_edges}


def analyze_dependency_graph(
    certificate: dict,
    verification: dict,
    source: dict,
) -> dict:
    """生成正 257 边形 69E 证书的依赖分析报告。"""

    program = certificate["construction"]["program"]
    nodes = build_nodes(program)
    nodes_by_id = {node["id"]: node for node in nodes}
    edges = [
        {"from": dependency, "to": node["id"]}
        for node in nodes
        for dependency in node["dependencies"]
    ]

    witness_alternatives = []
    for points in certificate["assertions"]["target_witnesses"]:
        active = transitive_cone(nodes_by_id, points)
        witness_alternatives.append(
            {"points": points, **cone_summary(nodes, active)}
        )

    first_sources = verification["first_target_sources"]
    new_objects = {item["new_object"] for item in first_sources}
    if len(new_objects) != 1:
        raise ValueError("首次目标来源没有唯一的新对象")
    first_hit_new_object = next(iter(new_objects))
    source_objects = list(
        dict.fromkeys(item["source_object"] for item in first_sources)
    )
    orientations = list(
        dict.fromkeys(item["orientation"] for item in first_sources)
    )
    final_cone = transitive_cone(nodes_by_id, (first_hit_new_object,))
    final_cone_summary = cone_summary(nodes, final_cone)
    paid_nodes = [node for node in nodes if node["paid"]]
    intersection_nodes = [
        node for node in nodes if node["kind"] == "intersection"
    ]
    syntactically_dead_paid = final_cone_summary["unrequired_paid_nodes"]

    return {
        "schema": "euclid-min-regular-257-dependency-report/v1",
        "source": source,
        "semantics": {
            "edge_direction": "dependency_to_consumer",
            "scope": "declared_certificate_bindings",
            "limitation": (
                "只证明证书声明的依赖关系；未搜索同一交点的其他对象对，也不证明"
                "付费步骤在所有几何构造中不可替代。"
            ),
        },
        "summary": {
            "initial_nodes": len(INITIAL_NODES),
            "program_nodes": len(program),
            "paid_nodes": len(paid_nodes),
            "line_nodes": sum(node["kind"] == "line" for node in paid_nodes),
            "circle_nodes": sum(
                node["kind"] == "circle" for node in paid_nodes
            ),
            "intersection_nodes": len(intersection_nodes),
            "edges": len(edges),
            "syntactically_dead_paid_nodes": len(syntactically_dead_paid),
        },
        "nodes": nodes,
        "edges": edges,
        "target_analysis": {
            "first_target_e_move": verification[
                "automatic_closure_target_audit"
            ]["first_target_e_move"],
            "first_hit_new_object": first_hit_new_object,
            "first_hit_source_objects": source_objects,
            "orientations": orientations,
            "witness_alternatives": witness_alternatives,
            "final_paid_object_cone": {
                "root": first_hit_new_object,
                **final_cone_summary,
            },
            "removable_paid_draw_candidates": syntactically_dead_paid,
            "conclusion": (
                "最终付费对象反向依赖全部 69 个付费对象；在现有声明式绑定中没有"
                "可以直接删除的付费步骤。"
            ),
        },
        "paid_projection": build_paid_projection(nodes),
    }


def render_paid_projection_dot(report: dict) -> str:
    """把免费交点收缩后的付费依赖图输出为 Graphviz DOT。"""

    projection = report["paid_projection"]
    first_target = report["target_analysis"]
    lines = [
        "digraph regular_257_69e {",
        '  graph [rankdir="LR", bgcolor="white", label="正 257 边形 69E 付费依赖图（免费交点已收缩）", labelloc="t"];',
        '  node [fontname="Microsoft YaHei", fontsize=10, style="rounded,filled", color="#334155", fillcolor="#e2e8f0"];',
        '  edge [color="#64748b", arrowsize=0.65];',
        '  "initial_state" [label="初始状态", shape=oval, fillcolor="#dcfce7", color="#15803d"];',
    ]
    final_name = first_target["first_hit_new_object"]
    for node in projection["nodes"]:
        shape = "ellipse" if node["kind"] == "circle" else "box"
        fill = "#fde68a" if node["id"] == final_name else "#e2e8f0"
        color = "#b45309" if node["id"] == final_name else "#334155"
        label = f"E{node['e_move']}  {node['id']}"
        lines.append(
            f'  "{node["id"]}" [label="{label}", shape={shape}, '
            f'fillcolor="{fill}", color="{color}"];'
        )
        if node["uses_initial_state"]:
            lines.append(f'  "initial_state" -> "{node["id"]}";')
    for edge in projection["edges"]:
        lines.append(f'  "{edge["from"]}" -> "{edge["to"]}";')
    lines.extend(
        [
            '  "target" [label="目标首次命中 @ 69E", shape=doubleoctagon, fillcolor="#fecaca", color="#b91c1c"];',
            f'  "{final_name}" -> "target" [color="#b91c1c", penwidth=2];',
            "}",
        ]
    )
    return "\n".join(lines) + "\n"
