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
