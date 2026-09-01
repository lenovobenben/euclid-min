"""审计 46E 状态中“新圆产生两点，再画跨尾部直线”的 2E 桥接模板。"""

from __future__ import annotations

import multiprocessing
import os
from itertools import combinations
from math import comb

from cyclotomic_replay import (
    FIELD,
    ORDER_FIELD,
    Circle,
    Line,
    intersection_points,
)
from full_intersection_closure import _point_key, build_runtime_arrangement
from geometry_algebra_ir import _algebra_system
from residual_point_ball_audit import (
    _real_ball,
    balls_may_overlap,
    exact_point_ball,
    line_circle_intersection_balls,
)
from tail_cross_pair_all_point_line_search import (
    _line_line_point,
    _radical_axis,
    _available_point_ids,
    _encoded_point,
    _macro,
    _materialize_available_balls,
)


_WORKER_STATE = None


def _squared_distance_ball(first: tuple, second: tuple):
    dx = first[0] - second[0]
    dy = first[1] - second[1]
    return dx * dx + dy * dy


def _scalar_key(value) -> tuple:
    try:
        return "FIELD", FIELD(value)
    except (TypeError, ValueError):
        return "UCF", ORDER_FIELD(value)


def _target_context(first, second) -> dict:
    dx = second.x - first.x
    dy = second.y - first.y
    return {
        "base": first,
        "dx": dx,
        "dy": dy,
        "norm_squared": dx * dx + dy * dy,
        "line": Line.through(first, second),
    }


def _point_parameter(point, context: dict):
    return (
        (point.x - context["base"].x) * context["dx"]
        + (point.y - context["base"].y) * context["dy"]
    ) / context["norm_squared"]


def _point_ball_parameter(point_ball: tuple, context: dict):
    base_ball = exact_point_ball(context["base"])
    dx_ball = _real_ball(context["dx"])
    dy_ball = _real_ball(context["dy"])
    norm_ball = _real_ball(context["norm_squared"])
    return (
        (point_ball[0] - base_ball[0]) * dx_ball
        + (point_ball[1] - base_ball[1]) * dy_ball
    ) / norm_ball


def _circle_parameter_polynomial(circle: Circle, context: dict) -> tuple:
    offset_x = context["base"].x - circle.center.x
    offset_y = context["base"].y - circle.center.y
    return (
        context["norm_squared"],
        2 * (context["dx"] * offset_x + context["dy"] * offset_y),
        offset_x * offset_x + offset_y * offset_y - circle.radius_squared,
    )


def _polynomial_value(polynomial: tuple, value):
    a, b, c = polynomial
    return (a * value + b) * value + c


def _bridge_points(context: dict, prefix_drawables: list[tuple[str, object]]) -> list[dict]:
    """返回目标直线与既有对象的全部不同交点及其既有对象见证。"""

    target = context["line"]
    records = []
    exact_records_by_key = {}
    drawable_values = dict(prefix_drawables)
    for drawable_name, drawable in prefix_drawables:
        if not isinstance(drawable, Line):
            continue
        point = _line_line_point(target, drawable)
        if point is None:
            continue
        key = _point_key(point)
        if key not in exact_records_by_key:
            record = {
                "point": point,
                "ball": exact_point_ball(point),
                "parameter": _point_parameter(point, context),
                "parameter_ball": None,
                "parameter_polynomial": None,
                "producer_circle": None,
                "witness_drawables": [],
            }
            exact_records_by_key[key] = record
            records.append(record)
        exact_records_by_key[key]["witness_drawables"].append(drawable_name)

    for drawable_name, drawable in prefix_drawables:
        if not isinstance(drawable, Circle):
            continue
        roots = line_circle_intersection_balls(
            (target.a, target.b, target.c),
            drawable,
        )
        for root_ball in roots:
            overlapping = [
                record
                for record in records
                if balls_may_overlap(record["ball"], root_ball)
            ]
            matches = []
            for record in overlapping:
                if record["point"] is not None:
                    same_point = drawable.contains(record["point"])
                else:
                    other_circle = drawable_values[record["producer_circle"]]
                    axis = _radical_axis(other_circle, drawable)
                    common = _line_line_point(target, axis)
                    same_point = (
                        common is not None
                        and other_circle.contains(common)
                        and drawable.contains(common)
                        and balls_may_overlap(exact_point_ball(common), root_ball)
                        and balls_may_overlap(exact_point_ball(common), record["ball"])
                    )
                if same_point:
                    matches.append(record)
            if len(matches) > 1:
                raise ValueError("一个严格圆交点分支匹配多个既有桥接点")
            if matches:
                matches[0]["witness_drawables"].append(drawable_name)
                continue
            if overlapping:
                raise ValueError("128 位严格实球不能区分两个不同桥接点")
            records.append(
                {
                    "point": None,
                    "ball": root_ball,
                    "parameter": None,
                    "parameter_ball": _point_ball_parameter(root_ball, context),
                    "parameter_polynomial": _circle_parameter_polynomial(
                        drawable,
                        context,
                    ),
                    "producer_circle": drawable_name,
                    "witness_drawables": [drawable_name],
                }
            )

    records.sort(
        key=lambda record: (
            float(record["ball"][0].center()),
            float(record["ball"][1].center()),
        ),
    )
    for index, record in enumerate(records):
        record["id"] = f"bridge.{index}"
        if record["parameter_ball"] is None:
            record["parameter_ball"] = _real_ball(record["parameter"])
        record["witness_drawables"].sort()
    return records


def _overlapping_radius_pairs(radius_balls: list) -> list[tuple[int, int]]:
    """用严格区间扫描返回所有可能相等的半径平方对。"""

    ordered = sorted(
        range(len(radius_balls)),
        key=lambda index: radius_balls[index].lower(),
    )
    active: list[int] = []
    survivors = []
    for index in ordered:
        current = radius_balls[index]
        active = [
            old_index
            for old_index in active
            if radius_balls[old_index].upper() >= current.lower()
        ]
        for old_index in active:
            if (radius_balls[old_index] - current).contains_zero():
                survivors.append((old_index, index))
        active.append(index)
    return survivors


def _exact_available_point(point_id: str, universe: dict, cache: dict):
    """仅在严格实球留下候选时物化一个抽象残余点的精确分支。"""

    if point_id in cache:
        return cache[point_id]
    point = universe["point_values"][point_id]
    if point is not None:
        cache[point_id] = point
        return point

    metadata = universe["abstract_metadata"][point_id]
    first_name, second_name = metadata["producer"]
    first = universe["drawable_values"][first_name]
    second = universe["drawable_values"][second_name]
    target_ball = universe["point_balls"][point_id]
    matches = [
        root
        for root in intersection_points(first, second)
        if balls_may_overlap(exact_point_ball(root), target_ball)
    ]
    if len(matches) != 1:
        raise ValueError(f"抽象点 {point_id} 不能唯一物化: {len(matches)} 个分支")
    cache[point_id] = matches[0]
    return matches[0]


def _record_root_of_polynomial(record: dict, polynomial: tuple) -> bool:
    """用一次二次消元判断指定参数分支是否为另一二次式的根。"""

    if record["parameter"] is not None:
        return _polynomial_value(polynomial, record["parameter"]) == 0
    producer = record["parameter_polynomial"]
    producer_a, producer_b, producer_c = producer
    target_a, target_b, target_c = polynomial
    linear = target_a * producer_b - producer_a * target_b
    constant = target_a * producer_c - producer_a * target_c
    if linear == 0:
        return constant == 0
    candidate = -constant / linear
    return (
        _polynomial_value(producer, candidate) == 0
        and _polynomial_value(polynomial, candidate) == 0
        and (_real_ball(candidate) - record["parameter_ball"]).contains_zero()
    )


def _bridge_point_on_circle(record: dict, context: dict, circle: Circle) -> bool:
    return _record_root_of_polynomial(
        record,
        _circle_parameter_polynomial(circle, context),
    )


def _bridge_pair_equidistant(
    center,
    context: dict,
    first: dict,
    second: dict,
) -> bool:
    """在目标线参数上用二次消元证明两个指定分支到圆心等距。"""

    h = (
        (center.x - context["base"].x) * context["dx"]
        + (center.y - context["base"].y) * context["dy"]
    ) / context["norm_squared"]
    reflected_sum = 2 * h
    first_parameter = first["parameter"]
    second_parameter = second["parameter"]
    if first_parameter is not None:
        candidate = reflected_sum - first_parameter
        return (
            _record_root_of_polynomial(
                second,
                (0, 1, -candidate),
            )
            and (_real_ball(candidate) - second["parameter_ball"]).contains_zero()
        )
    if second_parameter is not None:
        candidate = reflected_sum - second_parameter
        return (
            _record_root_of_polynomial(
                first,
                (0, 1, -candidate),
            )
            and (_real_ball(candidate) - first["parameter_ball"]).contains_zero()
        )

    second_a, second_b, second_c = second["parameter_polynomial"]
    reflected_second = (
        second_a,
        -2 * second_a * reflected_sum - second_b,
        second_a * reflected_sum * reflected_sum
        + second_b * reflected_sum
        + second_c,
    )
    first_a, first_b, first_c = first["parameter_polynomial"]
    reflected_a, reflected_b, reflected_c = reflected_second
    linear = reflected_a * first_b - first_a * reflected_b
    constant = reflected_a * first_c - first_a * reflected_c
    if linear == 0:
        return constant == 0 and (
            _real_ball(reflected_sum)
            - first["parameter_ball"]
            - second["parameter_ball"]
        ).contains_zero()
    candidate = -constant / linear
    reflected_candidate = reflected_sum - candidate
    return (
        _polynomial_value(first["parameter_polynomial"], candidate) == 0
        and _polynomial_value(
            second["parameter_polynomial"],
            reflected_candidate,
        )
        == 0
        and (_real_ball(candidate) - first["parameter_ball"]).contains_zero()
        and (
            _real_ball(reflected_candidate) - second["parameter_ball"]
        ).contains_zero()
    )


def _drawable_circles_for_bridge_pair(
    center,
    context: dict,
    first_bridge: dict,
    second_bridge: dict,
    bridge_radius_ball,
    available_radius_balls: list,
    universe: dict,
    exact_cache: dict,
) -> tuple[list[dict], int, int]:
    """从可用圆上点反向构造经过指定桥接点对的唯一同心圆。"""

    survivors = []
    exact_fallbacks = 0
    for point_record, available_radius in zip(
        universe["available_records"],
        available_radius_balls,
    ):
        if not (available_radius - bridge_radius_ball).contains_zero():
            continue
        survivors.append(point_record)
    ordered_survivors = sorted(
        survivors,
        key=lambda record: universe["point_values"][record["id"]] is None,
    )
    for point_record in ordered_survivors:
        exact_fallbacks += 1
        point_id = point_record["id"]
        through = _exact_available_point(point_id, universe, exact_cache)
        if through == center:
            continue
        circle = Circle.through(center, through)
        if not _bridge_point_on_circle(
            first_bridge,
            context,
            circle,
        ):
            continue
        if not _bridge_point_on_circle(
            second_bridge,
            context,
            circle,
        ):
            continue
        return (
            [
                {
                    "circle": circle,
                    "through_points": [point_id],
                }
            ],
            len(survivors),
            exact_fallbacks,
        )
    return [], len(survivors), exact_fallbacks


def _search_root_pair(task: tuple[int, str, str]) -> dict:
    """在 fork 继承的只读 46E 宇宙中审计一个跨尾部根对。"""

    if _WORKER_STATE is None:
        raise RuntimeError("两对象桥接工作进程尚未初始化")
    pair_index, low_symbol, high_symbol = task
    state = _WORKER_STATE
    universe = state["universe"]
    exact_cache = state["exact_cache"]
    available_ids = state["available_ids"]
    prefix_drawables = state["prefix_drawables"]
    prefix_circles = state["prefix_circles"]
    root_points = state["root_points"]

    context = _target_context(
        root_points[low_symbol],
        root_points[high_symbol],
    )
    bridges = _bridge_points(context, prefix_drawables)
    pair_space = len(available_ids) * comb(len(bridges), 2)
    pair_overlap_survivors = 0
    pair_exact_equalities = 0
    existing_circle_equalities = 0
    new_circle_geometries = 0
    through_point_checks = 0
    through_point_survivors = 0
    through_point_fallbacks = 0
    circle_candidates = []
    circle_records_by_key = {}

    for center_record in universe["available_records"]:
        center_id = center_record["id"]
        center_ball = universe["point_balls"][center_id]
        radius_balls = [
            _squared_distance_ball(center_ball, bridge["ball"])
            for bridge in bridges
        ]
        overlaps = _overlapping_radius_pairs(radius_balls)
        pair_overlap_survivors += len(overlaps)
        if not overlaps:
            continue

        center = _exact_available_point(center_id, universe, exact_cache)
        available_radius_balls = None
        for first_index, second_index in overlaps:
            first_bridge = bridges[first_index]
            second_bridge = bridges[second_index]
            if not _bridge_pair_equidistant(
                center,
                context,
                first_bridge,
                second_bridge,
            ):
                continue
            pair_exact_equalities += 1
            if available_radius_balls is None:
                center_exact_ball = exact_point_ball(center)
                available_radius_balls = [
                    _squared_distance_ball(
                        center_exact_ball,
                        universe["point_balls"][record["id"]],
                    )
                    for record in universe["available_records"]
                ]
            (
                drawable_circles,
                strict_through_survivors,
                exact_through_fallbacks,
            ) = _drawable_circles_for_bridge_pair(
                center,
                context,
                first_bridge,
                second_bridge,
                radius_balls[first_index],
                available_radius_balls,
                universe,
                exact_cache,
            )
            through_point_checks += len(available_ids)
            through_point_survivors += strict_through_survivors
            through_point_fallbacks += exact_through_fallbacks
            for drawable_circle in drawable_circles:
                circle = drawable_circle["circle"]
                circle_key = (center_id, _scalar_key(circle.radius_squared))
                if circle_key in circle_records_by_key:
                    existing_record = circle_records_by_key[circle_key]
                    existing_record["available_through_points"] = sorted(
                        set(existing_record["available_through_points"])
                        | set(drawable_circle["through_points"])
                    )
                    continue
                existing_refs = [
                    name
                    for name, existing in prefix_circles
                    if existing == circle
                ]
                if existing_refs:
                    existing_circle_equalities += 1
                else:
                    new_circle_geometries += 1
                candidate_record = {
                    "center": center_id,
                    "bridge_points": [
                        {
                            "id": first_bridge["id"],
                            "witness_drawables": first_bridge[
                                "witness_drawables"
                            ],
                        },
                        {
                            "id": second_bridge["id"],
                            "witness_drawables": second_bridge[
                                "witness_drawables"
                            ],
                        },
                    ],
                    "existing_drawable_references": existing_refs,
                    "available_through_points": drawable_circle[
                        "through_points"
                    ],
                    "strict_through_point_survivors": (
                        strict_through_survivors
                    ),
                    "exact_through_point_fallbacks": exact_through_fallbacks,
                    "is_new_drawable": not existing_refs,
                    "is_drawable_from_46e_state": not existing_refs,
                }
                circle_records_by_key[circle_key] = candidate_record
                circle_candidates.append(candidate_record)

    drawable_candidates = [
        candidate
        for candidate in circle_candidates
        if candidate["is_drawable_from_46e_state"]
    ]
    return {
        "pair_index": pair_index,
        "result": {
            "low_symbol": low_symbol,
            "high_symbol": high_symbol,
            "bridge_points": [
                {
                    "id": bridge["id"],
                    "witness_drawables": bridge["witness_drawables"],
                }
                for bridge in bridges
            ],
            "bridge_point_count": len(bridges),
            "center_bridge_pair_space": pair_space,
            "strict_radius_overlap_survivors": pair_overlap_survivors,
            "exact_equidistant_center_pairs": pair_exact_equalities,
            "circle_candidates": circle_candidates,
            "drawable_new_circle_candidates": drawable_candidates,
        },
        "metrics": {
            "center_bridge_pair_space": pair_space,
            "strict_radius_overlap_survivors": pair_overlap_survivors,
            "exact_radius_equalities": pair_exact_equalities,
            "existing_circle_equalities": existing_circle_equalities,
            "new_circle_geometries": new_circle_geometries,
            "through_point_checks": through_point_checks,
            "strict_through_point_survivors": through_point_survivors,
            "exact_through_point_fallbacks": through_point_fallbacks,
            "drawable_new_circle_candidates": len(drawable_candidates),
        },
    }


def search_two_object_line_bridges(
    certificate: dict,
    ga_ir: dict,
    source: dict,
    *,
    before_e: int = 46,
    workers: int | None = None,
    trace=None,
) -> dict:
    """完整审计“首笔新圆产生两点、次笔画目标直线”的桥接程序。"""

    if before_e != 46:
        raise ValueError("v1 报告冻结在 46E 状态")
    arrangement = build_runtime_arrangement(certificate, trace=trace)
    available_ids = _available_point_ids(ga_ir, before_e)
    universe = _materialize_available_balls(arrangement, available_ids)
    exact_cache = {
        point_id: point
        for point_id, point in universe["point_values"].items()
        if point_id in available_ids and point is not None
    }

    _symbols, _relations, values = _algebra_system()
    low_symbols = _macro(ga_ir, "macro.low-tail")["output_symbols"]
    high_symbols = _macro(ga_ir, "macro.high-tail")["output_symbols"]
    root_points = {
        symbol_id: _encoded_point(values[symbol_id])
        for symbol_id in [*low_symbols, *high_symbols]
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

    pair_tasks = [
        (pair_index, low_symbol, high_symbol)
        for pair_index, (low_symbol, high_symbol) in enumerate(
            (
                (low_symbol, high_symbol)
                for low_symbol in low_symbols
                for high_symbol in high_symbols
            ),
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
        "exact_cache": exact_cache,
        "available_ids": available_ids,
        "prefix_drawables": prefix_drawables,
        "prefix_circles": prefix_circles,
        "root_points": root_points,
    }
    parallel_outputs = []
    if worker_count > 1:
        if "fork" not in multiprocessing.get_all_start_methods():
            raise RuntimeError("完整点桥接并行搜索需要 Linux fork")
        context = multiprocessing.get_context("fork")
        with context.Pool(processes=worker_count) as pool:
            for output in pool.imap(_search_root_pair, pair_tasks, chunksize=1):
                parallel_outputs.append(output)
                if trace:
                    result = output["result"]
                    trace(
                        f"root_pair={output['pair_index']}/36 "
                        f"bridges={result['bridge_point_count']} "
                        f"overlaps={result['strict_radius_overlap_survivors']} "
                        f"exact={result['exact_equidistant_center_pairs']} "
                        f"drawable={len(result['drawable_new_circle_candidates'])}"
                    )
        pair_iterator = []
    else:
        pair_iterator = [
            (low_symbol, high_symbol)
            for low_symbol in low_symbols
            for high_symbol in high_symbols
        ]

    results = []
    total_pair_space = 0
    total_radius_overlap_survivors = 0
    total_exact_radius_equalities = 0
    total_existing_circle_equalities = 0
    total_new_circle_geometries = 0
    total_through_point_checks = 0
    total_through_point_survivors = 0
    total_through_point_fallbacks = 0
    candidate_root_pairs = []

    for pair_index, (low_symbol, high_symbol) in enumerate(
        pair_iterator,
        start=1,
    ):
        if trace:
            trace(f"root_pair={pair_index}/36 phase=bridge_points")
        context = _target_context(
            root_points[low_symbol],
            root_points[high_symbol],
        )
        bridges = _bridge_points(context, prefix_drawables)
        if trace:
            trace(
                f"root_pair={pair_index}/36 phase=center_scan bridges={len(bridges)}"
            )
        pair_space = len(available_ids) * comb(len(bridges), 2)
        total_pair_space += pair_space
        pair_overlap_survivors = 0
        pair_exact_equalities = 0
        circle_candidates = []
        circle_records_by_key = {}

        for center_index, center_record in enumerate(
            universe["available_records"],
            start=1,
        ):
            center_id = center_record["id"]
            center_ball = universe["point_balls"][center_id]
            radius_balls = [
                _squared_distance_ball(center_ball, bridge["ball"])
                for bridge in bridges
            ]
            overlaps = _overlapping_radius_pairs(radius_balls)
            pair_overlap_survivors += len(overlaps)
            total_radius_overlap_survivors += len(overlaps)
            if not overlaps:
                if trace and center_index % 100 == 0:
                    trace(
                        f"root_pair={pair_index}/36 centers={center_index}/989 "
                        f"overlaps={pair_overlap_survivors}"
                    )
                continue

            if trace:
                trace(
                    f"root_pair={pair_index}/36 center={center_index}/989 "
                    f"phase=exact_radius overlaps={len(overlaps)}"
                )

            center = _exact_available_point(center_id, universe, exact_cache)
            available_radius_balls = None
            for first_index, second_index in overlaps:
                first_bridge = bridges[first_index]
                second_bridge = bridges[second_index]
                if trace:
                    trace(
                        f"root_pair={pair_index}/36 center={center_index}/989 "
                        f"phase=reflection pair={first_index},{second_index}"
                    )
                equidistant = _bridge_pair_equidistant(
                    center,
                    context,
                    first_bridge,
                    second_bridge,
                )
                if trace:
                    trace(
                        f"root_pair={pair_index}/36 center={center_index}/989 "
                        f"phase=reflection_done equal={equidistant}"
                    )
                if not equidistant:
                    continue
                pair_exact_equalities += 1
                total_exact_radius_equalities += 1
                if available_radius_balls is None:
                    if trace:
                        trace(
                            f"root_pair={pair_index}/36 center={center_index}/989 "
                            "phase=available_radii"
                        )
                    center_exact_ball = exact_point_ball(center)
                    available_radius_balls = [
                        _squared_distance_ball(
                            center_exact_ball,
                            universe["point_balls"][record["id"]],
                        )
                        for record in universe["available_records"]
                    ]
                    if trace:
                        trace(
                            f"root_pair={pair_index}/36 center={center_index}/989 "
                            "phase=available_radii_done"
                        )
                if trace:
                    trace(
                        f"root_pair={pair_index}/36 center={center_index}/989 "
                        "phase=drawable_circles"
                    )
                (
                    drawable_circles,
                    strict_through_survivors,
                    exact_through_fallbacks,
                ) = _drawable_circles_for_bridge_pair(
                    center,
                    context,
                    first_bridge,
                    second_bridge,
                    radius_balls[first_index],
                    available_radius_balls,
                    universe,
                    exact_cache,
                )
                if trace:
                    trace(
                        f"root_pair={pair_index}/36 center={center_index}/989 "
                        f"phase=drawable_circles_done found={len(drawable_circles)} "
                        f"survivors={strict_through_survivors}"
                    )
                total_through_point_checks += len(available_ids)
                total_through_point_survivors += strict_through_survivors
                total_through_point_fallbacks += exact_through_fallbacks
                for drawable_circle in drawable_circles:
                    circle = drawable_circle["circle"]
                    circle_key = (center_id, _scalar_key(circle.radius_squared))
                    if circle_key in circle_records_by_key:
                        existing_record = circle_records_by_key[circle_key]
                        existing_record["available_through_points"] = sorted(
                            set(existing_record["available_through_points"])
                            | set(drawable_circle["through_points"])
                        )
                        continue
                    existing_refs = [
                        name
                        for name, existing in prefix_circles
                        if existing == circle
                    ]
                    if existing_refs:
                        total_existing_circle_equalities += 1
                    else:
                        total_new_circle_geometries += 1
                    candidate_record = {
                        "center": center_id,
                        "bridge_points": [
                            {
                                "id": first_bridge["id"],
                                "witness_drawables": first_bridge["witness_drawables"],
                            },
                            {
                                "id": second_bridge["id"],
                                "witness_drawables": second_bridge["witness_drawables"],
                            },
                        ],
                        "existing_drawable_references": existing_refs,
                        "available_through_points": drawable_circle[
                            "through_points"
                        ],
                        "strict_through_point_survivors": strict_through_survivors,
                        "exact_through_point_fallbacks": exact_through_fallbacks,
                        "is_new_drawable": not existing_refs,
                        "is_drawable_from_46e_state": not existing_refs,
                    }
                    circle_records_by_key[circle_key] = candidate_record
                    circle_candidates.append(candidate_record)
            if trace and center_index % 100 == 0:
                trace(
                    f"root_pair={pair_index}/36 centers={center_index}/989 "
                    f"overlaps={pair_overlap_survivors}"
                )

        drawable_candidates = [
            candidate
            for candidate in circle_candidates
            if candidate["is_drawable_from_46e_state"]
        ]
        if drawable_candidates:
            candidate_root_pairs.append([low_symbol, high_symbol])
        results.append(
            {
                "low_symbol": low_symbol,
                "high_symbol": high_symbol,
                "bridge_points": [
                    {
                        "id": bridge["id"],
                        "witness_drawables": bridge["witness_drawables"],
                    }
                    for bridge in bridges
                ],
                "bridge_point_count": len(bridges),
                "center_bridge_pair_space": pair_space,
                "strict_radius_overlap_survivors": pair_overlap_survivors,
                "exact_equidistant_center_pairs": pair_exact_equalities,
                "circle_candidates": circle_candidates,
                "drawable_new_circle_candidates": drawable_candidates,
            }
        )
        if trace:
            trace(
                f"root_pair={pair_index}/36 bridges={len(bridges)} "
                f"overlaps={pair_overlap_survivors} "
                f"exact={pair_exact_equalities} drawable={len(drawable_candidates)}"
            )

    if parallel_outputs:
        results = [output["result"] for output in parallel_outputs]
        total_pair_space = sum(
            output["metrics"]["center_bridge_pair_space"]
            for output in parallel_outputs
        )
        total_radius_overlap_survivors = sum(
            output["metrics"]["strict_radius_overlap_survivors"]
            for output in parallel_outputs
        )
        total_exact_radius_equalities = sum(
            output["metrics"]["exact_radius_equalities"]
            for output in parallel_outputs
        )
        total_existing_circle_equalities = sum(
            output["metrics"]["existing_circle_equalities"]
            for output in parallel_outputs
        )
        total_new_circle_geometries = sum(
            output["metrics"]["new_circle_geometries"]
            for output in parallel_outputs
        )
        total_through_point_checks = sum(
            output["metrics"]["through_point_checks"]
            for output in parallel_outputs
        )
        total_through_point_survivors = sum(
            output["metrics"]["strict_through_point_survivors"]
            for output in parallel_outputs
        )
        total_through_point_fallbacks = sum(
            output["metrics"]["exact_through_point_fallbacks"]
            for output in parallel_outputs
        )
        candidate_root_pairs = [
            [result["low_symbol"], result["high_symbol"]]
            for result in results
            if result["drawable_new_circle_candidates"]
        ]

    if len(results) != 36:
        raise AssertionError("两对象目标直线桥接审计没有覆盖 36 个根对")
    return {
        "schema": "euclid-min-tail-cross-pair-two-object-line-bridge-search/v1",
        "source": source,
        "semantics": {
            "state": "all_989_arrangement_points_available_after_46E",
            "template": "new_first_object_creates_two_points_then_new_target_line",
            "first_line_case": "impossible_because_two_distinct_lines_have_at_most_one_intersection",
            "searched_first_object": "new_circle_with_available_center_and_available_through_point",
            "second_object": "cross_tail_root_pair_line_through_two_new_bridge_points",
            "exactness": "128_bit_strict_real_ball_pruning_with_exact_target_line_parameter_polynomial_elimination",
        },
        "root_sets": {
            "low_tail": low_symbols,
            "high_tail": high_symbols,
        },
        "universe": {
            "available_points": len(available_ids),
            "exact_coordinate_points": universe["exact_points"],
            "abstract_residual_points": universe["abstract_points"],
            "prefix_drawables": len(prefix_drawables),
            "prefix_circles": len(prefix_circles),
            "ambiguous_point_pairs": [],
        },
        "summary": {
            "workers": worker_count,
            "cross_root_pairs": len(results),
            "center_bridge_pair_space": total_pair_space,
            "strict_radius_overlap_survivors": total_radius_overlap_survivors,
            "exact_radius_equalities": total_exact_radius_equalities,
            "existing_circle_equalities": total_existing_circle_equalities,
            "new_circle_geometries": total_new_circle_geometries,
            "through_point_checks": total_through_point_checks,
            "strict_through_point_survivors": total_through_point_survivors,
            "exact_through_point_fallbacks": total_through_point_fallbacks,
            "drawable_new_circle_candidates": sum(
                len(result["drawable_new_circle_candidates"])
                for result in results
            ),
            "root_pairs_with_2e_bridge": len(candidate_root_pairs),
        },
        "results": results,
        "candidate_root_pairs": candidate_root_pairs,
        "conclusion": {
            "status": (
                "candidate_found"
                if candidate_root_pairs
                else "exhausted_no_two_object_line_bridge"
            ),
            "minimality_claim": "none",
        },
        "limitations": [
            "只覆盖第二笔为跨尾部目标直线，且第一笔负责产生两个定位点的 2E 模板。",
            "不覆盖第二笔为圆，也不覆盖第一笔只产生一个新点而第二笔结合既有点的情形；后者已因目标直线上没有既有点而对直线目标自动排除。",
            "空结果只排除该有限两对象模板，不证明两个尾部的 18E 最优。",
        ],
    }
