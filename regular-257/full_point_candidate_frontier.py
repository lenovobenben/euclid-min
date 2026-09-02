"""M257-8：完整交点宇宙中的删二候选前沿审计。"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from math import comb

from full_intersection_closure import forward_full_closure


COORDINATE_ORIGINS = {
    "line_line",
    "circle_triple",
    "circle_circle_on_line",
}


def exact_coordinate_point_ids(arrangement: dict) -> set[str]:
    """返回当前实现可以直接恢复精确坐标的安排点。"""

    return {
        point["id"]
        for point in arrangement["points"]
        if point["origin"] in COORDINATE_ORIGINS or point["names"]
    }


def _frequency(values) -> list[dict]:
    return [
        {"value": value, "trials": count}
        for value, count in sorted(Counter(values).items())
    ]


def analyze_candidate_frontier(full_report: dict, source: dict) -> dict:
    """穷尽删二状态，量化单新对象画出以前可用的定义点前沿。"""

    arrangement = full_report["arrangement"]
    paid_ids = [drawable["id"] for drawable in arrangement["drawables"]]
    e_moves = {
        drawable["id"]: drawable["e_move"]
        for drawable in arrangement["drawables"]
    }
    paid_set = set(paid_ids)
    exact_ids = exact_coordinate_point_ids(arrangement)
    target_circle_point_ids = {
        point["id"]
        for point in arrangement["points"]
        if "c0" in point["incident_drawables"]
    }
    trials = []
    for first, second in combinations(paid_ids, 2):
        removed = (first, second)
        selected = paid_set.difference(removed)
        closure = forward_full_closure(arrangement, selected)
        available_points = closure["available_points"]
        available_paid = closure["available_drawables"].intersection(paid_set)
        available_exact = available_points.intersection(exact_ids)
        exact_count = len(available_exact)
        stalled_selected = selected.difference(available_paid)
        trials.append(
            {
                "removed": list(removed),
                "removed_e_moves": [e_moves[first], e_moves[second]],
                "includes_target_transfer": "target_transfer" in removed,
                "target_reached_before_candidate": closure["target_reached"],
                "available_points": len(available_points),
                "available_exact_coordinate_points": exact_count,
                "available_target_circle_points": len(
                    available_points.intersection(target_circle_point_ids)
                ),
                "available_paid_drawables": len(available_paid),
                "stalled_selected_drawables": len(stalled_selected),
                "line_definition_upper_bound": comb(exact_count, 2),
                "circle_definition_upper_bound": exact_count * (exact_count - 1),
            }
        )

    ranked = sorted(
        trials,
        key=lambda trial: (
            -trial["available_exact_coordinate_points"],
            -trial["available_paid_drawables"],
            trial["removed_e_moves"],
        ),
    )
    target_transfer_trials = [
        trial for trial in trials if trial["includes_target_transfer"]
    ]
    exact_counts = [
        trial["available_exact_coordinate_points"] for trial in trials
    ]
    paid_counts = [trial["available_paid_drawables"] for trial in trials]
    return {
        "schema": "euclid-min-regular-257-full-point-candidate-frontier/v1",
        "source": source,
        "semantics": {
            "point_universe": (
                "all_finite_real_intersections_of_the_70_existing_drawables"
            ),
            "candidate_definition_points": (
                "available_points_with_materialized_exact_coordinates"
            ),
            "schedule": "closure_before_adding_one_new_drawable",
            "purpose": (
                "量化每个删二状态在加入单个新对象以前可使用的精确定义点前沿；"
                "本报告本身不枚举或排除新对象。"
            ),
        },
        "inventory": {
            "points": len(arrangement["points"]),
            "exact_coordinate_points": len(exact_ids),
            "abstract_residual_points": len(arrangement["points"]) - len(exact_ids),
            "target_circle_points": len(target_circle_point_ids),
            "paid_drawables": len(paid_ids),
            "removed_pairs": len(trials),
        },
        "summary": {
            "trials_reaching_target_before_candidate": sum(
                trial["target_reached_before_candidate"] for trial in trials
            ),
            "minimum_available_exact_coordinate_points": min(exact_counts),
            "maximum_available_exact_coordinate_points": max(exact_counts),
            "minimum_available_paid_drawables": min(paid_counts),
            "maximum_available_paid_drawables": max(paid_counts),
            "target_transfer_trials": len(target_transfer_trials),
            "maximum_frontier_trials": ranked[:20],
            "exact_point_count_frequency": _frequency(exact_counts),
            "available_paid_drawable_count_frequency": _frequency(paid_counts),
        },
        "trials": trials,
    }
