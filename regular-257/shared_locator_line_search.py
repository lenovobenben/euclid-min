"""搜索一条可从 46E 状态画出、同时生产多个根载线定位点的新直线。"""

from __future__ import annotations

import multiprocessing
import os
from itertools import combinations

from cyclotomic_replay import Line
from full_intersection_closure import _point_key, build_runtime_arrangement
from geometry_algebra_ir import _algebra_system
from tail_cross_pair_all_point_line_search import (
    _abstract_point_on_line,
    _available_point_ids,
    _encoded_point,
    _materialize_available_balls,
)
from tail_cross_pair_two_object_line_bridge_search import (
    _bridge_points,
    _scalar_key,
    _target_context,
)


_WORKER_STATE = None


def _line_key(line: Line) -> tuple:
    return (
        _scalar_key(line.a),
        _scalar_key(line.b),
        _scalar_key(line.c),
    )


def _available_line_definitions(
    first_bridge: dict,
    second_bridge: dict,
    coefficient_balls: tuple,
    universe: dict,
) -> tuple[list[str], dict, Line | None]:
    """严格筛选并精确确认目标线是否至少经过两个 46E 可用点。"""

    ball_a, ball_b, ball_c = coefficient_balls
    incident = []
    checks = 0
    survivors = 0
    exact_fallbacks = 0
    abstract_fallbacks = 0
    target = None
    for point_record in universe["available_records"]:
        point_id = point_record["id"]
        x, y = universe["point_balls"][point_id]
        checks += 1
        if not (ball_a * x + ball_b * y + ball_c).contains_zero():
            continue
        survivors += 1
        if target is None:
            target = Line.through(
                first_bridge["point"],
                second_bridge["point"],
            )
        point = universe["point_values"][point_id]
        if point is not None:
            exact_fallbacks += 1
            on_line = target.contains(point)
        else:
            abstract_fallbacks += 1
            on_line = _abstract_point_on_line(point_id, target, universe)
        if on_line:
            incident.append(point_id)
            if len(incident) == 2:
                break
    return (
        incident,
        {
            "strict_ball_checks": checks,
            "strict_ball_survivors": survivors,
            "exact_coordinate_fallbacks": exact_fallbacks,
            "abstract_incidence_fallbacks": abstract_fallbacks,
        },
        target,
    )


def _locator_effects(line: Line, target_tasks: list[dict]) -> list[dict]:
    effects = []
    for task in target_tasks:
        locators = []
        seen_points = set()
        for bridge in task["bridges"]:
            point = bridge["point"]
            key = _point_key(point)
            if key in seen_points or not line.contains(point):
                continue
            seen_points.add(key)
            locators.append(
                {
                    "bridge": bridge["id"],
                    "witness_drawables": bridge["witness_drawables"],
                    "already_available_at_46e": key
                    in task["available_locator_keys"],
                }
            )
        if locators:
            effects.append(
                {
                    "task": task["id"],
                    "baseline_carrier": task["baseline_carrier"],
                    "locators": locators,
                    "new_locator_count": sum(
                        not locator["already_available_at_46e"]
                        for locator in locators
                    ),
                }
            )
    return effects


def _search_task_pair(task_pair: tuple[int, int, int]) -> dict:
    if _WORKER_STATE is None:
        raise RuntimeError("共享定位点直线搜索工作进程尚未初始化")
    pair_index, first_index, second_index = task_pair
    state = _WORKER_STATE
    first_task = state["target_tasks"][first_index]
    second_task = state["target_tasks"][second_index]
    prefix_lines = state["prefix_lines"]
    universe = state["universe"]

    bridge_pair_space = 0
    coincident_bridge_pairs = 0
    candidate_line_occurrences = 0
    duplicate_constructible_lines = 0
    constructible_existing_line_equalities = 0
    constructible_new_lines = 0
    metrics = {
        "strict_ball_checks": 0,
        "strict_ball_survivors": 0,
        "exact_coordinate_fallbacks": 0,
        "abstract_incidence_fallbacks": 0,
    }
    seen_lines = set()
    constructible_candidates = []
    for first_bridge in first_task["bridges"]:
        for second_bridge in second_task["bridges"]:
            bridge_pair_space += 1
            if first_bridge["point"] == second_bridge["point"]:
                coincident_bridge_pairs += 1
                continue
            candidate_line_occurrences += 1
            first_x, first_y = first_bridge["ball"]
            second_x, second_y = second_bridge["ball"]
            coefficient_balls = (
                first_y - second_y,
                second_x - first_x,
                first_x * second_y - second_x * first_y,
            )
            definitions, line_metrics, line = _available_line_definitions(
                first_bridge,
                second_bridge,
                coefficient_balls,
                universe,
            )
            for key in metrics:
                metrics[key] += line_metrics[key]
            if len(definitions) < 2:
                continue
            if line is None:
                raise AssertionError("已有两个定义点却没有构造精确候选线")
            line_key = _line_key(line)
            if line_key in seen_lines:
                duplicate_constructible_lines += 1
                continue
            seen_lines.add(line_key)
            existing_refs = [
                name for name, existing in prefix_lines if existing == line
            ]
            if existing_refs:
                constructible_existing_line_equalities += 1
                continue
            constructible_new_lines += 1
            effects = _locator_effects(line, state["target_tasks"])
            new_task_count = sum(
                effect["new_locator_count"] > 0 for effect in effects
            )
            new_locator_count = sum(
                effect["new_locator_count"] for effect in effects
            )
            constructible_candidates.append(
                {
                    "_line_key": line_key,
                    "origin_task_pair": [first_task["id"], second_task["id"]],
                    "origin_bridges": [first_bridge["id"], second_bridge["id"]],
                    "definition_points": definitions,
                    "locator_effects": effects,
                    "new_task_count": new_task_count,
                    "new_locator_count": new_locator_count,
                    "qualifies_as_shared_new_locator": new_task_count >= 2,
                }
            )
    return {
        "pair_index": pair_index,
        "task_pair": [first_task["id"], second_task["id"]],
        "bridge_pair_space": bridge_pair_space,
        "coincident_bridge_pairs": coincident_bridge_pairs,
        "candidate_line_occurrences": candidate_line_occurrences,
        "distinct_constructible_lines": len(seen_lines),
        "duplicate_constructible_lines": duplicate_constructible_lines,
        "constructible_existing_line_equalities": (
            constructible_existing_line_equalities
        ),
        "constructible_new_lines": constructible_new_lines,
        **metrics,
        "constructible_candidates": constructible_candidates,
    }


def _target_tasks(
    chord_ir: dict,
    exact_relations: list[dict],
    values: dict,
    prefix_drawables: list[tuple[str, object]],
    universe: dict,
) -> list[dict]:
    relation_by_id = {relation["id"]: relation for relation in exact_relations}
    tasks = []
    for task in chord_ir["tasks"]:
        relation = relation_by_id[task["relation"]]
        first = _encoded_point(values[relation["roots"][0]])
        second = _encoded_point(values[relation["roots"][1]])
        context = _target_context(first, second)
        bridges = _bridge_points(context, prefix_drawables)
        materialized = []
        deferred_circle_only_bridges = 0
        for bridge in bridges:
            # 与既有直线的交点在主分圆域中可直接物化。只由既有圆产生的
            # 二次分支保留给下一分片的参数多项式实现，避免在这里展开高代价根坐标。
            if bridge["point"] is None:
                deferred_circle_only_bridges += 1
                continue
            point = bridge["point"]
            materialized.append(
                {
                    "id": f"{task['id']}.{bridge['id']}",
                    "point": point,
                    "ball": bridge["ball"],
                    "witness_drawables": bridge["witness_drawables"],
                }
            )
        available_locator_keys = {
            _point_key(universe["point_values"][point_id])
            for point_id in task["available_incident_points_at_46e"]
            if universe["point_values"][point_id] is not None
        }
        if len(available_locator_keys) != len(
            task["available_incident_points_at_46e"]
        ):
            raise ValueError("根载线已有定位点中出现未物化的抽象点")
        tasks.append(
            {
                "id": task["id"],
                "branch": task["branch"],
                "relation": task["relation"],
                "baseline_carrier": task["baseline_carrier"],
                "bridges": materialized,
                "deferred_circle_only_bridges": deferred_circle_only_bridges,
                "available_locator_keys": available_locator_keys,
            }
        )
    return tasks


def search_shared_locator_lines(
    certificate: dict,
    ga_ir: dict,
    chord_ir: dict,
    source: dict,
    *,
    before_e: int = 46,
    workers: int | None = None,
    trace=None,
) -> dict:
    """穷尽跨两条根载线桥接点的、可由 46E 点定义的新直线。"""

    if before_e != 46:
        raise ValueError("v1 报告冻结在 46E 状态")
    arrangement = build_runtime_arrangement(certificate, trace=trace)
    available_ids = _available_point_ids(ga_ir, before_e)
    universe = _materialize_available_balls(arrangement, available_ids)
    prefix_drawables = [
        ("c0", universe["drawable_values"]["c0"]),
        *[
            (drawable["id"], universe["drawable_values"][drawable["id"]])
            for drawable in arrangement["drawables"]
            if drawable["e_move"] <= before_e
        ],
    ]
    prefix_lines = [
        (name, drawable)
        for name, drawable in prefix_drawables
        if isinstance(drawable, Line)
    ]
    _symbols, exact_relations, values = _algebra_system()
    target_tasks = _target_tasks(
        chord_ir,
        exact_relations,
        values,
        prefix_drawables,
        universe,
    )

    pair_tasks = [
        (pair_index, first, second)
        for pair_index, (first, second) in enumerate(
            combinations(range(len(target_tasks)), 2),
            start=1,
        )
    ]
    requested_workers = workers if workers is not None else min(8, os.cpu_count() or 1)
    worker_count = min(requested_workers, len(pair_tasks))
    if worker_count < 1:
        raise ValueError("工作进程数必须为正数")
    global _WORKER_STATE
    _WORKER_STATE = {
        "universe": universe,
        "prefix_lines": prefix_lines,
        "target_tasks": target_tasks,
    }
    if worker_count > 1:
        if "fork" not in multiprocessing.get_all_start_methods():
            raise RuntimeError("共享定位点并行搜索需要 Linux fork")
        context = multiprocessing.get_context("fork")
        with context.Pool(processes=worker_count) as pool:
            outputs = []
            for output in pool.imap(_search_task_pair, pair_tasks, chunksize=1):
                outputs.append(output)
                if trace:
                    trace(
                        f"task_pair={output['pair_index']}/{len(pair_tasks)} "
                        f"space={output['bridge_pair_space']} "
                        f"constructible_lines={output['constructible_new_lines']} "
                        f"constructible={len(output['constructible_candidates'])}"
                    )
    else:
        outputs = [_search_task_pair(task) for task in pair_tasks]
    _WORKER_STATE = None
    outputs.sort(key=lambda item: item["pair_index"])

    unique_candidates = {}
    for output in outputs:
        for candidate in output["constructible_candidates"]:
            key = candidate.pop("_line_key")
            if key not in unique_candidates:
                unique_candidates[key] = candidate
                candidate["origin_task_pairs"] = [candidate.pop("origin_task_pair")]
                candidate["origin_bridge_pairs"] = [candidate.pop("origin_bridges")]
                continue
            existing = unique_candidates[key]
            existing["origin_task_pairs"].append(candidate["origin_task_pair"])
            existing["origin_bridge_pairs"].append(candidate["origin_bridges"])
            existing["definition_points"] = sorted(
                set(existing["definition_points"])
                | set(candidate["definition_points"])
            )[:2]
    candidates = list(unique_candidates.values())
    for index, candidate in enumerate(candidates, start=1):
        candidate["id"] = f"shared-locator-line.{index}"
        candidate["origin_task_pairs"].sort()
        candidate["origin_bridge_pairs"].sort()
    shared_candidates = [
        candidate
        for candidate in candidates
        if candidate["qualifies_as_shared_new_locator"]
    ]

    result_rows = []
    for output in outputs:
        row = dict(output)
        row["constructible_candidate_count"] = len(
            row.pop("constructible_candidates")
        )
        result_rows.append(row)
    summary_keys = (
        "bridge_pair_space",
        "coincident_bridge_pairs",
        "candidate_line_occurrences",
        "distinct_constructible_lines",
        "duplicate_constructible_lines",
        "constructible_existing_line_equalities",
        "constructible_new_lines",
        "strict_ball_checks",
        "strict_ball_survivors",
        "exact_coordinate_fallbacks",
        "abstract_incidence_fallbacks",
    )
    summary = {key: sum(row[key] for row in result_rows) for key in summary_keys}
    summary.update(
        {
            "workers": worker_count,
            "available_points": len(available_ids),
            "exact_coordinate_points": universe["exact_points"],
            "abstract_residual_points": universe["abstract_points"],
            "prefix_drawables": len(prefix_drawables),
            "tail_chord_tasks": len(target_tasks),
            "task_pairs": len(pair_tasks),
            "constructible_candidate_occurrences": sum(
                row["constructible_candidate_count"] for row in result_rows
            ),
            "distinct_constructible_new_lines": len(candidates),
            "shared_new_locator_lines": len(shared_candidates),
        }
    )
    return {
        "schema": "euclid-min-regular-257-shared-locator-line-search/v1",
        "source": source,
        "semantics": {
            "input_state": "complete_46e_free_intersection_closure",
            "bridge_point": (
                "intersection of one tail root chord and one existing prefix line"
            ),
            "candidate": (
                "one new line through bridge points from two distinct root-chord tasks, "
                "drawable through two 46E available points"
            ),
            "success": (
                "the new line materializes previously unavailable locator points for at "
                "least two root-chord tasks"
            ),
            "exactness": "exact_line_line_bridges_then_128_bit_strict_real_ball_incidence",
            "scope": (
                "complete for prefix-line witnesses; circle-only bridge branches are "
                "deferred in polynomial form"
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
                    "deferred_circle_only_bridge_count": task[
                        "deferred_circle_only_bridges"
                    ],
                }
                for task in target_tasks
            ],
            "ambiguous_available_point_balls": [],
        },
        "summary": summary,
        "results": result_rows,
        "constructible_new_line_candidates": candidates,
        "shared_new_locator_candidates": shared_candidates,
        "conclusion": {
            "status": (
                "candidate_found"
                if shared_candidates
                else "exhausted_no_shared_locator_line_with_prefix_line_witness"
            ),
            "minimality_claim": "none",
            "next": (
                "exactly replay candidates and test 17E joint-tail schedules"
                if shared_candidates
                else "extend bridge points to circle-only polynomial branches"
            ),
        },
        "limitations": [
            "本分片完整覆盖由 46E 既有直线见证的桥接点。",
            "只由既有圆见证的二次桥接分支尚未展开；下一分片将沿目标线参数保留其二次多项式。",
            "找到共享定位点仍只是一项局部原语，必须放入 17E 联合尾部调度后才能确认净省步。",
        ],
    }
