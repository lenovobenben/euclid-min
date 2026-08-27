"""把搜索路径转换为带确定性交点绑定的正式证书。"""

from __future__ import annotations

from pathlib import Path

from ..canonical_json import sha256_hex
from ..formats import load_profile
from ..geometry import Drawable, Point
from ..intersections import IntersectionKind, intersect
from ..replay import ProgramReplayer
from ..state import GeometryState
from ..target import reached_targets
from .model import SearchStep


def build_program_from_steps(
    steps: tuple[SearchStep, ...],
) -> tuple[list[dict], GeometryState]:
    """重放路径并为首次用到的隐式交点插入零成本绑定。"""

    state = GeometryState.fixed_initial()
    point_names: list[tuple[Point, str]] = [
        (state.points[0], "O"),
        (state.points[1], "A"),
    ]
    object_names: list[tuple[Drawable, str]] = [
        (state.circles[0], "unit_circle")
    ]
    program: list[dict] = []
    point_counter = 0
    line_counter = 0
    circle_counter = 0

    def point_name(point: Point) -> str:
        nonlocal point_counter
        for existing, name in point_names:
            if existing == point:
                return name
        for first_index, (first, first_name) in enumerate(object_names):
            for second, second_name in object_names[first_index + 1 :]:
                result = intersect(first, second)
                if result.kind == IntersectionKind.COINCIDENT:
                    continue
                for intersection_index, candidate in enumerate(result.points):
                    if candidate != point:
                        continue
                    point_counter += 1
                    name = f"P{point_counter}"
                    program.append(
                        {
                            "id": name,
                            "op": "intersect",
                            "objects": [first_name, second_name],
                            "index": intersection_index,
                        }
                    )
                    point_names.append((point, name))
                    return name
        raise ValueError("搜索路径引用了当前自动闭包中不存在的点")

    for step in steps:
        first_name = point_name(step.first)
        second_name = point_name(step.second)
        if step.op == "line":
            line_counter += 1
            object_name = f"L{line_counter}"
            entry = {
                "id": object_name,
                "op": "line",
                "through": [first_name, second_name],
            }
            addition = state.draw_line(step.first, step.second)
        elif step.op == "circle":
            circle_counter += 1
            object_name = f"C{circle_counter}"
            entry = {
                "id": object_name,
                "op": "circle",
                "center": first_name,
                "through": second_name,
            }
            addition = state.draw_circle(step.first, step.second)
        else:
            raise ValueError(f"不支持的搜索操作 {step.op!r}")
        if not addition.new_object:
            raise ValueError("搜索路径包含重复绘制对象")
        program.append(entry)
        object_names.append((addition.object, object_name))

    return program, state


def build_certificate_from_steps(
    steps: tuple[SearchStep, ...],
    *,
    profile_path: str | Path,
    construction_id: str = "search-candidate",
    title: str = "Euclid-Min exact search candidate",
) -> dict:
    """只为已命中当前正十七边形目标的路径生成正式证书。"""

    profile = load_profile(profile_path)
    program, state = build_program_from_steps(steps)
    targets = [target.value for target in reached_targets(state.points)]
    if not targets:
        raise ValueError("搜索路径没有命中当前 profile 的目标")
    construction = {
        "id": construction_id,
        "title": title,
        "description": "Candidate produced by bounded exact breadth-first search.",
        "program": program,
    }
    return {
        "schema": "euclid-min-certificate/v1",
        "problem": profile.data["problem"]["id"],
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "construction": construction,
        "assertions": {
            "score": {"metric": "e_move", "e_move": len(steps)},
            "targets": targets,
            "claim": "verified_construction",
        },
        "software": {
            "producer": {"name": "euclid-min-sage-search", "version": "1"},
            "solver": {"name": "bounded-breadth-first", "version": "1"},
        },
        "integrity": {"construction_sha256": sha256_hex(construction)},
    }


def steps_from_program(program: list[dict]) -> tuple[SearchStep, ...]:
    """从本模块导出的程序恢复不含 ID 的搜索路径。"""

    replay = ProgramReplayer().replay(program)
    steps: list[SearchStep] = []
    for entry in program:
        if entry["op"] == "line":
            first, second = (
                replay.names[reference] for reference in entry["through"]
            )
            steps.append(SearchStep("line", first, second))
        elif entry["op"] == "circle":
            steps.append(
                SearchStep(
                    "circle",
                    replay.names[entry["center"]],
                    replay.names[entry["through"]],
                )
            )
    return tuple(steps)


def node_from_steps(steps: tuple[SearchStep, ...]):
    """用搜索器的完整闭包语义重建 checkpoint 节点。"""

    from .model import Candidate, SearchNode

    node = SearchNode.initial()
    for step in steps:
        node = node.apply(Candidate(step.op, step.first, step.second))
    return node
