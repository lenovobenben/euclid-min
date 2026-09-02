"""搜索一笔可从 46E 状态画出、同时生产多个根载线定位点的新圆。"""

from __future__ import annotations

import json
import multiprocessing
import os
from itertools import combinations

from cyclotomic_replay import Circle
from full_intersection_closure import _point_key, build_runtime_arrangement
from geometry_algebra_ir import _algebra_system
from residual_point_ball_audit import exact_point_ball
from tail_cross_pair_all_point_line_search import (
    _available_point_ids,
    _encoded_point,
    _materialize_available_balls,
)
from tail_cross_pair_two_object_line_bridge_search import (
    _bridge_point_on_circle,
    _bridge_points,
    _exact_available_point,
    _scalar_key,
    _squared_distance_ball,
    _target_context,
)


_WORKER_STATE = None


def _cross_radius_overlaps(first: list, second: list) -> list[tuple[int, int]]:
    return [
        (first_index, second_index)
        for first_index, first_radius in enumerate(first)
        for second_index, second_radius in enumerate(second)
        if (first_radius - second_radius).contains_zero()
    ]


def _existing_circle_witness(
    center,
    first_bridge: dict,
    second_bridge: dict,
    prefix_circle_by_id: dict,
) -> str | None:
    common = set(first_bridge["witness_drawables"]) & set(
        second_bridge["witness_drawables"]
    )
    for name in sorted(common):
        circle = prefix_circle_by_id.get(name)
        if circle is not None and circle.center == center:
            return name
    return None


def _available_circle_for_bridges(
    center,
    center_id: str,
    target_radius_ball,
    available_radius_balls: list,
    first_task: dict,
    first_bridge: dict,
    second_task: dict,
    second_bridge: dict,
    state: dict,
) -> tuple[Circle | None, str | None, int, int]:
    universe = state["universe"]
    survivors = [
        record
        for record, radius_ball in zip(
            universe["available_records"],
            available_radius_balls,
        )
        if (radius_ball - target_radius_ball).contains_zero()
    ]
    ordered = sorted(
        survivors,
        key=lambda record: universe["point_values"][record["id"]] is None,
    )
    fallbacks = 0
    for record in ordered:
        point_id = record["id"]
        if point_id == center_id:
            continue
        fallbacks += 1
        point = _exact_available_point(
            point_id,
            universe,
            state["exact_available_cache"],
        )
        if point == center:
            continue
        circle = Circle.through(center, point)
        if not _bridge_point_on_circle(
            first_bridge,
            first_task["context"],
            circle,
        ):
            continue
        if not _bridge_point_on_circle(
            second_bridge,
            second_task["context"],
            circle,
        ):
            continue
        return circle, point_id, len(survivors), fallbacks
    return None, None, len(survivors), fallbacks


def _search_task_pair(task_pair: tuple[int, int, int]) -> dict:
    if _WORKER_STATE is None:
        raise RuntimeError("共享定位点圆搜索工作进程尚未初始化")
    pair_index, first_index, second_index = task_pair
    state = _WORKER_STATE
    universe = state["universe"]
    first_task = state["target_tasks"][first_index]
    second_task = state["target_tasks"][second_index]
    bridge_pair_space = (
        len(universe["available_records"])
        * len(first_task["bridges"])
        * len(second_task["bridges"])
    )
    coincident_bridge_pairs = 0
    strict_radius_overlap_survivors = 0
    exact_existing_circle_shortcuts = 0
    exact_drawable_radius_equalities = 0
    new_circle_geometries = 0
    through_point_checks = 0
    strict_through_point_survivors = 0
    exact_through_point_fallbacks = 0
    seen_circles = set()
    drawable_candidates = []

    for center_record in universe["available_records"]:
        center_id = center_record["id"]
        center_ball = universe["point_balls"][center_id]
        first_radii = [
            _squared_distance_ball(center_ball, bridge["ball"])
            for bridge in first_task["bridges"]
        ]
        second_radii = [
            _squared_distance_ball(center_ball, bridge["ball"])
            for bridge in second_task["bridges"]
        ]
        overlaps = _cross_radius_overlaps(first_radii, second_radii)
        strict_radius_overlap_survivors += len(overlaps)
        if not overlaps:
            continue
        center = _exact_available_point(
            center_id,
            universe,
            state["exact_available_cache"],
        )
        available_radius_balls = None
        for first_bridge_index, second_bridge_index in overlaps:
            first_bridge = first_task["bridges"][first_bridge_index]
            second_bridge = second_task["bridges"][second_bridge_index]
            if (
                first_bridge["point"] is not None
                and second_bridge["point"] is not None
                and first_bridge["point"] == second_bridge["point"]
            ):
                coincident_bridge_pairs += 1
                continue
            existing_witness = _existing_circle_witness(
                center,
                first_bridge,
                second_bridge,
                state["prefix_circle_by_id"],
            )
            if existing_witness is not None:
                exact_existing_circle_shortcuts += 1
                exact_drawable_radius_equalities += 1
                continue
            if available_radius_balls is None:
                center_exact_ball = exact_point_ball(center)
                available_radius_balls = [
                    _squared_distance_ball(
                        center_exact_ball,
                        universe["point_balls"][record["id"]],
                    )
                    for record in universe["available_records"]
                ]
            through_point_checks += len(universe["available_records"])
            (
                circle,
                through_id,
                strict_survivors,
                exact_fallbacks,
            ) = _available_circle_for_bridges(
                center,
                center_id,
                first_radii[first_bridge_index],
                available_radius_balls,
                first_task,
                first_bridge,
                second_task,
                second_bridge,
                state,
            )
            strict_through_point_survivors += strict_survivors
            exact_through_point_fallbacks += exact_fallbacks
            if circle is None or through_id is None:
                continue
            exact_drawable_radius_equalities += 1
            existing_refs = [
                name
                for name, existing in state["prefix_circles"]
                if existing == circle
            ]
            if existing_refs:
                exact_existing_circle_shortcuts += 1
                continue
            circle_key = (center_id, _scalar_key(circle.radius_squared))
            if circle_key in seen_circles:
                continue
            seen_circles.add(circle_key)
            new_circle_geometries += 1
            selected = [
                (first_task, first_bridge),
                (second_task, second_bridge),
            ]
            locator_effects = [
                {
                    "task": task["id"],
                    "baseline_carrier": task["baseline_carrier"],
                    "bridge": bridge["id"],
                    "witness_drawables": bridge["witness_drawables"],
                    "already_available_at_46e": bridge[
                        "already_available_at_46e"
                    ],
                }
                for task, bridge in selected
            ]
            new_task_count = sum(
                not effect["already_available_at_46e"]
                for effect in locator_effects
            )
            drawable_candidates.append(
                {
                    "origin_task_pair": [first_task["id"], second_task["id"]],
                    "center": center_id,
                    "through_point": through_id,
                    "locator_effects": locator_effects,
                    "new_task_count": new_task_count,
                    "qualifies_as_shared_new_locator": new_task_count >= 2,
                }
            )

    result = {
        "pair_index": pair_index,
        "task_pair": [first_task["id"], second_task["id"]],
        "center_bridge_pair_space": bridge_pair_space,
        "coincident_bridge_pairs": coincident_bridge_pairs,
        "strict_radius_overlap_survivors": strict_radius_overlap_survivors,
        "exact_existing_circle_shortcuts": exact_existing_circle_shortcuts,
        "exact_drawable_radius_equalities": exact_drawable_radius_equalities,
        "new_circle_geometries": new_circle_geometries,
        "through_point_checks": through_point_checks,
        "strict_through_point_survivors": strict_through_point_survivors,
        "exact_through_point_fallbacks": exact_through_point_fallbacks,
        "drawable_candidates": drawable_candidates,
    }
    # multiprocessing 不应直接 pickle Sage/PARI 标量。这里既是运行时断言，
    # 也把可能由 Sage 算术产生的 int/bool 子类规范成标准 JSON 类型。
    return json.loads(json.dumps(result, ensure_ascii=False))


def _target_tasks(
    chord_ir: dict,
    exact_relations: list[dict],
    values: dict,
    prefix_drawables: list[tuple[str, object]],
    universe: dict,
) -> list[dict]:
    relation_by_id = {relation["id"]: relation for relation in exact_relations}
    tasks = []
    for task_index, task in enumerate(chord_ir["tasks"]):
        relation = relation_by_id[task["relation"]]
        context = _target_context(
            _encoded_point(values[relation["roots"][0]]),
            _encoded_point(values[relation["roots"][1]]),
        )
        records = _bridge_points(context, prefix_drawables)
        available_keys = {
            _point_key(universe["point_values"][point_id])
            for point_id in task["available_incident_points_at_46e"]
            if universe["point_values"][point_id] is not None
        }
        bridges = []
        for bridge in records:
            record = dict(bridge)
            record["id"] = f"{task['id']}.{bridge['id']}"
            record["task_index"] = task_index
            record["already_available_at_46e"] = (
                record["point"] is not None
                and _point_key(record["point"]) in available_keys
            )
            bridges.append(record)
        tasks.append(
            {
                "id": task["id"],
                "branch": task["branch"],
                "relation": task["relation"],
                "baseline_carrier": task["baseline_carrier"],
                "context": context,
                "bridges": bridges,
            }
        )
    return tasks


def search_shared_locator_circles(
    certificate: dict,
    ga_ir: dict,
    chord_ir: dict,
    source: dict,
    *,
    before_e: int = 46,
    workers: int | None = None,
    pair_indices: set[int] | None = None,
    trace=None,
) -> dict:
    """穷尽可用圆心/圆上点定义、跨两个根载线桥接点的新圆。"""

    if before_e != 46:
        raise ValueError("v1 报告冻结在 46E 状态")
    arrangement = build_runtime_arrangement(certificate, trace=trace)
    available_ids = _available_point_ids(ga_ir, before_e)
    universe = _materialize_available_balls(arrangement, available_ids)
    exact_available_cache = {
        point_id: point
        for point_id, point in universe["point_values"].items()
        if point_id in available_ids and point is not None
    }
    prefix_drawables = [
        ("c0", universe["drawable_values"]["c0"]),
        *[
            (drawable["id"], universe["drawable_values"][drawable["id"]])
            for drawable in arrangement["drawables"]
            if drawable["e_move"] <= before_e
        ],
    ]
    prefix_circles = [
        (name, drawable)
        for name, drawable in prefix_drawables
        if isinstance(drawable, Circle)
    ]
    _symbols, exact_relations, values = _algebra_system()
    target_tasks = _target_tasks(
        chord_ir,
        exact_relations,
        values,
        prefix_drawables,
        universe,
    )
    all_pair_tasks = [
        (pair_index, first, second)
        for pair_index, (first, second) in enumerate(
            combinations(range(len(target_tasks)), 2),
            start=1,
        )
    ]
    pair_tasks = [
        task
        for task in all_pair_tasks
        if pair_indices is None or task[0] in pair_indices
    ]
    if not pair_tasks:
        raise ValueError("没有选中任何根载线任务对")
    requested_workers = workers if workers is not None else min(8, os.cpu_count() or 1)
    worker_count = min(requested_workers, len(pair_tasks))
    if worker_count < 1:
        raise ValueError("工作进程数必须为正数")
    global _WORKER_STATE
    _WORKER_STATE = {
        "universe": universe,
        "exact_available_cache": exact_available_cache,
        "prefix_circles": prefix_circles,
        "prefix_circle_by_id": dict(prefix_circles),
        "target_tasks": target_tasks,
    }
    if worker_count > 1:
        if "fork" not in multiprocessing.get_all_start_methods():
            raise RuntimeError("共享定位点圆并行搜索需要 Linux fork")
        context = multiprocessing.get_context("fork")
        with context.Pool(processes=worker_count) as pool:
            outputs = []
            for output in pool.imap(_search_task_pair, pair_tasks, chunksize=1):
                outputs.append(output)
                if trace:
                    trace(
                        f"task_pair={output['pair_index']}/{len(pair_tasks)} "
                        f"overlaps={output['strict_radius_overlap_survivors']} "
                        f"exact_drawable={output['exact_drawable_radius_equalities']} "
                        f"drawable={len(output['drawable_candidates'])}"
                    )
    else:
        outputs = [_search_task_pair(task) for task in pair_tasks]
    _WORKER_STATE = None
    outputs.sort(key=lambda item: item["pair_index"])

    unique_candidates = {}
    for output in outputs:
        for candidate in output["drawable_candidates"]:
            center = _exact_available_point(
                candidate["center"],
                universe,
                exact_available_cache,
            )
            through = _exact_available_point(
                candidate["through_point"],
                universe,
                exact_available_cache,
            )
            rebuilt_circle = Circle.through(center, through)
            key = (
                candidate["center"],
                _scalar_key(rebuilt_circle.radius_squared),
            )
            if key not in unique_candidates:
                candidate["origin_task_pairs"] = [candidate.pop("origin_task_pair")]
                unique_candidates[key] = candidate
            else:
                unique_candidates[key]["origin_task_pairs"].append(
                    candidate["origin_task_pair"]
                )
    candidates = list(unique_candidates.values())
    for index, candidate in enumerate(candidates, start=1):
        candidate["id"] = f"shared-locator-circle.{index}"
        candidate["origin_task_pairs"].sort()
    shared_candidates = [
        candidate
        for candidate in candidates
        if candidate["qualifies_as_shared_new_locator"]
    ]

    result_rows = []
    metric_keys = (
        "center_bridge_pair_space",
        "coincident_bridge_pairs",
        "strict_radius_overlap_survivors",
        "exact_existing_circle_shortcuts",
        "exact_drawable_radius_equalities",
        "new_circle_geometries",
        "through_point_checks",
        "strict_through_point_survivors",
        "exact_through_point_fallbacks",
    )
    for output in outputs:
        row = dict(output)
        row["drawable_candidate_count"] = len(row.pop("drawable_candidates"))
        result_rows.append(row)
    summary = {key: sum(row[key] for row in result_rows) for key in metric_keys}
    summary.update(
        {
            "workers": worker_count,
            "available_points": len(available_ids),
            "exact_coordinate_points": universe["exact_points"],
            "abstract_residual_points": universe["abstract_points"],
            "prefix_drawables": len(prefix_drawables),
            "prefix_circles": len(prefix_circles),
            "tail_chord_tasks": len(target_tasks),
            "task_pairs": len(pair_tasks),
            "complete_task_pair_space": pair_indices is None,
            "distinct_drawable_new_circles": len(candidates),
            "shared_new_locator_circles": len(shared_candidates),
        }
    )
    return {
        "schema": "euclid-min-regular-257-shared-locator-circle-search/v1",
        "source": source,
        "semantics": {
            "input_state": "complete_46e_free_intersection_closure",
            "bridge_point": (
                "intersection of one tail root chord and any existing prefix drawable"
            ),
            "candidate": (
                "one circle centered at an available point, through an available point, "
                "and through bridge points from two distinct root-chord tasks"
            ),
            "success": (
                "the new circle materializes previously unavailable locator points for "
                "at least two root-chord tasks"
            ),
            "exactness": (
                "128_bit strict radius balls, existing-circle witness shortcut, then "
                "exact candidate circles from available through-points with polynomial "
                "bridge-incidence verification"
            ),
        },
        "universe": {
            "target_tasks": [
                {
                    "id": task["id"],
                    "branch": task["branch"],
                    "relation": task["relation"],
                    "baseline_carrier": task["baseline_carrier"],
                    "bridge_point_count": len(task["bridges"]),
                    "line_witness_bridge_count": sum(
                        bridge["point"] is not None for bridge in task["bridges"]
                    ),
                    "circle_only_bridge_count": sum(
                        bridge["point"] is None for bridge in task["bridges"]
                    ),
                }
                for task in target_tasks
            ],
            "ambiguous_available_point_balls": [],
        },
        "summary": summary,
        "results": result_rows,
        "drawable_new_circle_candidates": candidates,
        "shared_new_locator_candidates": shared_candidates,
        "conclusion": {
            "status": (
                "candidate_found"
                if shared_candidates
                else "exhausted_no_shared_locator_circle"
            ),
            "minimality_claim": "none",
            "next": (
                "exactly replay candidates and test 17E joint-tail schedules"
                if shared_candidates
                else "generate multi-object locator programs or alternative algebraic tasks"
            ),
        },
        "limitations": [
            "本搜索只覆盖一笔新圆；新圆心或新半径见证需要先由另一笔产生的程序不在本分片中。",
            "即使找到共享定位点，也必须放入完整 17E 联合尾部调度验证净成本。",
        ],
    }
