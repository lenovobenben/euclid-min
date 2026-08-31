"""构造程序的直接依赖、祖先闭包和目标根审计。"""

from __future__ import annotations

from dataclasses import dataclass

from ..replay import ProgramReplayer


INITIAL_DEPENDENCIES = {
    "O": (),
    "A": (),
    "unit_circle": ("O", "A"),
}


@dataclass(frozen=True, slots=True)
class PaidAncestryAudit:
    """给定根集合下计费对象是否全部位于祖先闭包。"""

    roots: tuple[str, ...]
    ancestors: frozenset[str]
    paid_objects: frozenset[str]
    non_ancestor_paid_objects: frozenset[str]

    @property
    def all_paid_objects_are_ancestors(self) -> bool:
        return not self.non_ancestor_paid_objects


@dataclass(frozen=True, slots=True)
class ReverseDependencyNode:
    """一项反向义务节点及其在裁剪后见证中的最早可用分数。"""

    node_id: str
    operation: str
    value_kind: str
    dependencies: tuple[str, ...]
    paid_cost: int
    paid_index: int | None
    availability_score: int


@dataclass(frozen=True, slots=True)
class ReverseDependencyCut:
    """在给定 E-score 切开一个具体反向见证所得的后缀接口。"""

    score: int
    roots: tuple[str, ...]
    boundary: tuple[str, ...]
    boundary_points: tuple[str, ...]
    boundary_drawables: tuple[str, ...]
    suffix_nodes: tuple[str, ...]
    suffix_paid_nodes: tuple[str, ...]

    @property
    def suffix_paid_cost(self) -> int:
        return len(self.suffix_paid_nodes)


@dataclass(frozen=True, slots=True)
class ReverseDependencyDag:
    """从目标根指向全部必要前提的、已裁剪具体见证 DAG。

    这不是所有可能构造的枚举；它把一条具体成功程序规范化为可在不同
    E-score 处切分的反向义务，用于校准未来的完备反向搜索。
    """

    roots: tuple[str, ...]
    nodes: tuple[ReverseDependencyNode, ...]

    @property
    def total_paid_cost(self) -> int:
        return sum(node.paid_cost for node in self.nodes)

    def node(self, node_id: str) -> ReverseDependencyNode:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(node_id)

    def cut(self, score: int) -> ReverseDependencyCut:
        """返回后缀尚未满足的节点，以及前向侧必须提供的最小边界。"""

        if score < 0:
            raise ValueError("反向依赖切分分数不能为负数")

        nodes_by_id = {node.node_id: node for node in self.nodes}
        boundary: set[str] = set()
        suffix: set[str] = set()
        pending = list(self.roots)
        while pending:
            node_id = pending.pop()
            if node_id in boundary or node_id in suffix:
                continue
            node = nodes_by_id[node_id]
            if node.availability_score <= score:
                boundary.add(node_id)
                continue
            suffix.add(node_id)
            pending.extend(node.dependencies)

        ordered_boundary = tuple(
            node.node_id for node in self.nodes if node.node_id in boundary
        )
        ordered_suffix = tuple(
            node.node_id for node in self.nodes if node.node_id in suffix
        )
        return ReverseDependencyCut(
            score=score,
            roots=self.roots,
            boundary=ordered_boundary,
            boundary_points=tuple(
                node_id
                for node_id in ordered_boundary
                if nodes_by_id[node_id].value_kind == "point"
            ),
            boundary_drawables=tuple(
                node_id
                for node_id in ordered_boundary
                if nodes_by_id[node_id].value_kind == "drawable"
            ),
            suffix_nodes=ordered_suffix,
            suffix_paid_nodes=tuple(
                node_id
                for node_id in ordered_suffix
                if nodes_by_id[node_id].paid_cost == 1
            ),
        )


def direct_dependencies(entry: dict) -> tuple[str, ...]:
    """返回一个规范程序条目的直接依赖 ID。"""

    operation = entry["op"]
    if operation == "line":
        return tuple(entry["through"])
    if operation == "circle":
        return (entry["center"], entry["through"])
    if operation == "intersect":
        return tuple(entry["objects"])
    raise ValueError(f"不支持的程序操作 {operation!r}")


def build_dependency_map(program: list[dict]) -> dict[str, tuple[str, ...]]:
    """构造拓扑有序的直接依赖表并检查引用。"""

    dependencies = dict(INITIAL_DEPENDENCIES)
    for entry in program:
        entry_id = entry["id"]
        if entry_id in dependencies:
            raise ValueError(f"重复依赖节点 ID {entry_id!r}")
        direct = direct_dependencies(entry)
        missing = tuple(reference for reference in direct if reference not in dependencies)
        if missing:
            raise ValueError(
                f"依赖节点 {entry_id!r} 引用了尚未出现的 ID {missing!r}"
            )
        dependencies[entry_id] = direct
    return dependencies


def dependency_ancestors(
    program: list[dict],
    roots: tuple[str, ...] | list[str],
) -> frozenset[str]:
    """返回根节点及其全部递归直接依赖。"""

    dependencies = build_dependency_map(program)
    root_tuple = tuple(roots)
    missing = tuple(root for root in root_tuple if root not in dependencies)
    if missing:
        raise ValueError(f"未知依赖根 {missing!r}")

    live: set[str] = set()
    pending = list(root_tuple)
    while pending:
        node_id = pending.pop()
        if node_id in live:
            continue
        live.add(node_id)
        pending.extend(dependencies[node_id])
    return frozenset(live)


def audit_paid_ancestry(
    program: list[dict],
    roots: tuple[str, ...] | list[str],
) -> PaidAncestryAudit:
    """报告哪些计费对象不属于指定目标根的依赖祖先。"""

    root_tuple = tuple(roots)
    ancestors = dependency_ancestors(program, root_tuple)
    paid_objects = frozenset(
        entry["id"]
        for entry in program
        if entry["op"] in {"line", "circle"}
    )
    return PaidAncestryAudit(
        roots=root_tuple,
        ancestors=ancestors,
        paid_objects=paid_objects,
        non_ancestor_paid_objects=paid_objects - ancestors,
    )


def prune_program_to_ancestors(
    program: list[dict],
    roots: tuple[str, ...] | list[str],
) -> list[dict]:
    """删除指定根依赖闭包以外的程序条目。"""

    ancestors = dependency_ancestors(program, roots)
    return [entry for entry in program if entry["id"] in ancestors]


def first_target_draw_id(program: list[dict]) -> str:
    """精确重放并返回首次产生正十七边形目标的计费对象 ID。"""

    replay = ProgramReplayer().replay(program)
    program_index = replay.first_target_program_index
    if program_index is None:
        raise ValueError("程序没有命中正十七边形目标")
    entry = program[program_index]
    if entry["op"] not in {"line", "circle"}:
        raise RuntimeError("目标首次出现必须发生在新对象绘制之后")
    return entry["id"]


def audit_first_target_ancestry(program: list[dict]) -> PaidAncestryAudit:
    """以首次产生目标的对象为根审计全部计费对象。"""

    return audit_paid_ancestry(program, (first_target_draw_id(program),))


def build_reverse_dependency_dag(
    program: list[dict],
    roots: tuple[str, ...] | list[str],
) -> ReverseDependencyDag:
    """把一条具体程序裁剪并规范化为目标根的反向依赖 DAG。

    ``availability_score`` 按裁剪后计费对象的顺序计算。交点节点的分数是
    两个父对象分数的最大值，而不是该名称在程序中出现时的累计分数；这与
    profile 的自动交点闭包语义一致。
    """

    root_tuple = tuple(dict.fromkeys(roots))
    if not root_tuple:
        raise ValueError("反向依赖 DAG 至少需要一个根节点")
    live = dependency_ancestors(program, root_tuple)
    node_specs = [
        ("O", "initial_point", "point", ()),
        ("A", "initial_point", "point", ()),
        ("unit_circle", "initial_circle", "drawable", ("O", "A")),
    ]
    node_specs.extend(
        (
            entry["id"],
            entry["op"],
            "point" if entry["op"] == "intersect" else "drawable",
            direct_dependencies(entry),
        )
        for entry in program
        if entry["id"] in live
    )

    nodes: list[ReverseDependencyNode] = []
    availability: dict[str, int] = {}
    paid_index = 0
    for node_id, operation, value_kind, dependencies in node_specs:
        if node_id not in live:
            continue
        paid_cost = int(operation in {"line", "circle"})
        current_paid_index: int | None = None
        if paid_cost:
            paid_index += 1
            current_paid_index = paid_index
        dependency_score = max(
            (availability[dependency] for dependency in dependencies),
            default=0,
        )
        node_score = (
            max(dependency_score, current_paid_index)
            if current_paid_index is not None
            else dependency_score
        )
        availability[node_id] = node_score
        nodes.append(
            ReverseDependencyNode(
                node_id=node_id,
                operation=operation,
                value_kind=value_kind,
                dependencies=dependencies,
                paid_cost=paid_cost,
                paid_index=current_paid_index,
                availability_score=node_score,
            )
        )

    # ``dependency_ancestors`` 已验证引用；这一断言额外防止规范化遗漏节点。
    missing = live - {node.node_id for node in nodes}
    if missing:
        raise RuntimeError(f"反向依赖 DAG 遗漏节点 {sorted(missing)!r}")
    return ReverseDependencyDag(roots=root_tuple, nodes=tuple(nodes))
