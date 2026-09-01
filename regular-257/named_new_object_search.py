"""M257-7：由 83 个具名点定义的单个新对象局部替换搜索。"""

from __future__ import annotations

from itertools import combinations
from math import comb

from sage.all import ComplexBallField

from cyclotomic_replay import (
    Circle,
    Line,
    squared_distance,
)
from semantic_dependency import exact_replay_universe


def collinear(first, second, third) -> bool:
    return (
        (second.x - first.x) * (third.y - first.y)
        - (second.y - first.y) * (third.x - first.x)
        == 0
    )


BALL_FIELD = ComplexBallField(128)


def real_ball_point(point):
    """把精确点严格包入 128 位实球区间。"""

    # 主坐标域是复分圆域，即使这些几何坐标都已知为实数，也不能直接
    # 强制转换到 RealBallField。先取严格复球嵌入，再取其实部，仍然是
    # 对真实坐标的严格区间包围。
    return BALL_FIELD(point.x).real(), BALL_FIELD(point.y).real()


def ball_may_be_collinear(first, second, third) -> bool:
    """仅在实球区间尚不能排除共线时返回真。"""

    determinant = (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )
    return determinant.contains_zero()


def enumerate_rich_candidates(
    certificate: dict,
    collinear_triples: list[list[int]],
    ball_points=None,
) -> tuple[list[dict], dict]:
    """从已验证的共线三元组和等距组生成真正能解锁具名点的新对象。"""

    replay = exact_replay_universe(certificate)
    point_items = replay["point_items"]
    drawable_items = replay["drawable_items"]
    point_names = [name for name, _point in point_items]
    point_values = [point for _name, point in point_items]
    if ball_points is None:
        ball_points = [real_ball_point(point) for point in point_values]
    point_pairs = list(combinations(range(len(point_items)), 2))
    pair_indices = {pair: index for index, pair in enumerate(point_pairs)}
    parent = list(range(len(point_pairs)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    active_pairs: set[int] = set()
    for first, second, third in collinear_triples:
        triple_pairs = (
            pair_indices[(first, second)],
            pair_indices[(first, third)],
            pair_indices[(second, third)],
        )
        active_pairs.update(triple_pairs)
        union(triple_pairs[0], triple_pairs[1])
        union(triple_pairs[0], triple_pairs[2])

    components: dict[int, set[int]] = {}
    for pair_index in active_pairs:
        root = find(pair_index)
        components.setdefault(root, set()).update(point_pairs[pair_index])

    old_lines = [
        drawable
        for _name, drawable in drawable_items
        if isinstance(drawable, Line)
    ]
    line_point_sets = sorted(
        (tuple(sorted(indices)) for indices in components.values()),
        key=lambda indices: tuple(point_names[index] for index in indices),
    )
    new_line_sets = []
    for indices in line_point_sets:
        line = Line.through(point_values[indices[0]], point_values[indices[1]])
        if not any(line == old_line for old_line in old_lines):
            new_line_sets.append(indices)

    candidates = []
    for indices in new_line_sets:
        incident = [point_names[index] for index in indices]
        candidates.append(
            {
                "id": f"NL{len(candidates) + 1:04d}",
                "kind": "line",
                "canonical_definition": incident[:2],
                "incident_named_points": incident,
                "definition_count": comb(len(incident), 2),
            }
        )

    old_circles = [
        drawable
        for _name, drawable in drawable_items
        if isinstance(drawable, Circle)
    ]
    circle_groups = []
    circle_radius_pairs = 0
    circle_ball_excluded_pairs = 0
    circle_exact_distance_checks = 0
    for center_index, center in enumerate(point_values):
        through_indices = [
            index for index in range(len(point_values)) if index != center_index
        ]
        center_ball = ball_points[center_index]
        radius_balls = {}
        for through_index in through_indices:
            through_ball = ball_points[through_index]
            dx = center_ball[0] - through_ball[0]
            dy = center_ball[1] - through_ball[1]
            radius_balls[through_index] = dx * dx + dy * dy
        parent_by_point = {index: index for index in through_indices}

        def find_point(index: int) -> int:
            while parent_by_point[index] != index:
                parent_by_point[index] = parent_by_point[parent_by_point[index]]
                index = parent_by_point[index]
            return index

        exact_distances = {}
        active_through_points = set()
        for first_index, second_index in combinations(through_indices, 2):
            circle_radius_pairs += 1
            if not (
                radius_balls[first_index] - radius_balls[second_index]
            ).contains_zero():
                circle_ball_excluded_pairs += 1
                continue
            circle_exact_distance_checks += 1
            for index in (first_index, second_index):
                if index not in exact_distances:
                    exact_distances[index] = squared_distance(
                        center, point_values[index]
                    )
            if exact_distances[first_index] != exact_distances[second_index]:
                continue
            first_root = find_point(first_index)
            second_root = find_point(second_index)
            if first_root != second_root:
                parent_by_point[second_root] = first_root
            active_through_points.update((first_index, second_index))
        radius_groups: dict[int, list[int]] = {}
        for through_index in active_through_points:
            radius_groups.setdefault(find_point(through_index), []).append(
                through_index
            )
        for group in radius_groups.values():
            group.sort()
            circle = Circle.through(center, point_values[group[0]])
            if any(circle == old_circle for old_circle in old_circles):
                continue
            circle_groups.append((center_index, tuple(group)))
    circle_groups.sort(
        key=lambda item: (
            point_names[item[0]],
            tuple(point_names[index] for index in item[1]),
        )
    )
    line_candidate_count = len(candidates)
    for center_index, through_indices in circle_groups:
        through_names = [point_names[index] for index in through_indices]
        candidates.append(
            {
                "id": f"NC{len(candidates) - line_candidate_count + 1:04d}",
                "kind": "circle",
                "canonical_definition": [
                    point_names[center_index],
                    through_names[0],
                ],
                "center": point_names[center_index],
                "incident_named_points": through_names,
                "definition_count": len(through_names),
            }
        )

    return candidates, {
        "named_points": len(point_items),
        "point_pairs": len(point_pairs),
        "point_triples": comb(len(point_items), 3),
        "collinear_triples": len(collinear_triples),
        "rich_line_geometries": len(line_point_sets),
        "new_rich_line_candidates": line_candidate_count,
        "new_rich_circle_candidates": len(circle_groups),
        "circle_radius_pairs": circle_radius_pairs,
        "circle_ball_excluded_pairs": circle_ball_excluded_pairs,
        "circle_exact_distance_checks": circle_exact_distance_checks,
    }


def _old_hypergraph(semantic_report: dict) -> dict:
    source = semantic_report["hypergraph"]
    point_ids = [*source["initial_points"], *[item["id"] for item in source["points"]]]
    point_order = {name: index for index, name in enumerate(point_ids)}
    drawable_ids = [
        *source["initial_drawables"],
        *[item["id"] for item in source["drawables"]],
    ]
    point_incident_drawables = {
        item["id"]: set(item["incident_drawables_in_final_state"])
        for item in source["points"]
    }
    drawable_conditions = []
    for item in source["drawables"]:
        if item["kind"] == "line":
            condition = {
                "kind": "line",
                "incident_points": set(item["incident_named_points"]),
            }
        else:
            definitions = item["exact_named_point_definitions"]
            condition = {
                "kind": "circle",
                "center_points": {pair[0] for pair in definitions},
                "through_points": {pair[1] for pair in definitions},
            }
        drawable_conditions.append((item["id"], condition))
    return {
        "point_ids": point_ids,
        "point_order": point_order,
        "initial_points": set(source["initial_points"]),
        "initial_drawables": set(source["initial_drawables"]),
        "paid_drawables": [item["id"] for item in source["drawables"]],
        "point_incident_drawables": point_incident_drawables,
        "drawable_conditions": drawable_conditions,
        "target_witnesses": source["target_witnesses"],
        "drawable_ids": drawable_ids,
    }


def closure_with_candidate(
    hypergraph: dict,
    selected_paid: set[str],
    candidate: dict,
) -> dict:
    """只使用具名点，允许一个新对象参与的单调前向闭包。"""

    available_points = set(hypergraph["initial_points"])
    available_drawables = set(hypergraph["initial_drawables"])
    candidate_available = False
    candidate_points = set(candidate["incident_named_points"])
    while True:
        old_state = (
            len(available_points),
            len(available_drawables),
            candidate_available,
        )
        for point_name, incident in hypergraph["point_incident_drawables"].items():
            if point_name in available_points:
                continue
            producer_count = len(incident.intersection(available_drawables))
            if candidate_available and point_name in candidate_points:
                producer_count += 1
            if producer_count >= 2:
                available_points.add(point_name)
        for name, condition in hypergraph["drawable_conditions"]:
            if name not in selected_paid or name in available_drawables:
                continue
            if condition["kind"] == "line":
                ready = (
                    len(condition["incident_points"].intersection(available_points))
                    >= 2
                )
            else:
                ready = bool(
                    condition["center_points"].intersection(available_points)
                ) and bool(
                    condition["through_points"].intersection(available_points)
                )
            if ready:
                available_drawables.add(name)
        if not candidate_available:
            if candidate["kind"] == "line":
                candidate_ready = len(candidate_points.intersection(available_points)) >= 2
            else:
                candidate_ready = (
                    candidate["center"] in available_points
                    and bool(candidate_points.intersection(available_points))
                )
            if candidate_ready:
                candidate_available = True
        new_state = (
            len(available_points),
            len(available_drawables),
            candidate_available,
        )
        if new_state == old_state:
            break
    reached_witnesses = [
        pair
        for pair in hypergraph["target_witnesses"]
        if all(point in available_points for point in pair)
    ]
    return {
        "target_reached": bool(reached_witnesses),
        "reached_target_witnesses": reached_witnesses,
        "available_points": available_points,
        "available_drawables": available_drawables,
        "candidate_available": candidate_available,
    }


def search_named_replacements(
    semantic_report: dict,
    candidates: list[dict],
    state: dict | None = None,
    progress=None,
    checkpoint=None,
    checkpoint_interval: int = 100,
) -> dict:
    """穷举删除两个旧对象并加入一个新对象的全部 68E 组合。"""

    hypergraph = _old_hypergraph(semantic_report)
    paid_ids = hypergraph["paid_drawables"]
    paid_set = set(paid_ids)
    removed_pairs = list(combinations(paid_ids, 2))
    if state is None:
        state = {
            "target_score": 68,
            "removed_old_draws": 2,
            "added_new_draws": 1,
            "removed_pairs_tested": 0,
            "next_removed_pair_index": 0,
            "candidate_count": len(candidates),
            "closure_trials": 0,
            "constructible_candidate_trials": 0,
            "solutions": [],
            "solutions_found": 0,
            "status": "running",
        }
    if state["candidate_count"] != len(candidates):
        raise ValueError("检查点候选数与当前候选列表不一致")
    start_index = state["next_removed_pair_index"]
    for zero_based_index in range(start_index, len(removed_pairs)):
        removed = removed_pairs[zero_based_index]
        selected = paid_set.difference(removed)
        for candidate in candidates:
            result = closure_with_candidate(hypergraph, selected, candidate)
            state["closure_trials"] += 1
            if result["candidate_available"]:
                state["constructible_candidate_trials"] += 1
            if result["target_reached"]:
                state["solutions"].append(
                    {
                        "removed": list(removed),
                        "candidate": candidate["id"],
                        "reached_target_witnesses": result[
                            "reached_target_witnesses"
                        ],
                    }
                )
        state["next_removed_pair_index"] = zero_based_index + 1
        state["removed_pairs_tested"] = zero_based_index + 1
        state["solutions_found"] = len(state["solutions"])
        if checkpoint and (
            state["next_removed_pair_index"] % checkpoint_interval == 0
        ):
            checkpoint(state)
        if progress and state["next_removed_pair_index"] % 250 == 0:
            progress(
                f"removed_pairs={state['next_removed_pair_index']}/"
                f"{len(removed_pairs)}"
            )
    state["status"] = (
        "solution_found" if state["solutions"] else "exhausted_no_solution"
    )
    state["solutions_found"] = len(state["solutions"])
    if checkpoint:
        checkpoint(state)
    return state
