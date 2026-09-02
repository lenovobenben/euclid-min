"""用 46E 完整点闭包审计跨尾部根对的一笔直线联合产出。"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from math import comb

from cyclotomic_replay import Circle, Line, Point
from full_intersection_closure import build_runtime_arrangement
from geometry_algebra_ir import _algebra_system
from residual_point_ball_audit import (
    _producer_pair,
    _real_ball,
    balls_may_overlap,
    circle_circle_intersection_balls,
    exact_point_ball,
    line_circle_intersection_balls,
)


def _macro(ga_ir: dict, macro_id: str) -> dict:
    matches = [
        macro
        for macro in ga_ir["baseline_macro_partition"]
        if macro["id"] == macro_id
    ]
    if len(matches) != 1:
        raise ValueError(f"宏 {macro_id} 不是唯一记录")
    return matches[0]


def _encoded_point(value) -> Point:
    denominator = value * value + 1
    return Point(
        2 * value / denominator,
        (1 - value * value) / denominator,
    )


def _line_line_point(first: Line, second: Line) -> Point | None:
    determinant = first.a * second.b - second.a * first.b
    if determinant == 0:
        return None
    return Point(
        (first.b * second.c - second.b * first.c) / determinant,
        (first.c * second.a - second.c * first.a) / determinant,
    )


def _radical_axis(first: Circle, second: Circle) -> Line:
    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    if dx == 0 and dy == 0:
        raise ValueError("同心圆没有唯一根轴")
    return Line(
        2 * dx,
        2 * dy,
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius_squared
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius_squared,
    )


def _available_point_ids(ga_ir: dict, before_e: int) -> set[str]:
    result = {"B", "C"}
    for transition in ga_ir["transitions"]:
        if transition["e_move"] > before_e:
            break
        result.update(transition["free_points_born"])
    return result


def _materialize_available_balls(
    arrangement: dict,
    available_ids: set[str],
) -> dict:
    point_values = arrangement["_runtime_point_values"]
    drawable_values = arrangement["_runtime_drawable_values"]
    available_records = [
        point for point in arrangement["points"] if point["id"] in available_ids
    ]
    if len(available_records) != len(available_ids):
        raise ValueError("46E 可用点 ID 与运行时安排不一致")
    exact_records = [
        point for point in available_records if point_values[point["id"]] is not None
    ]
    abstract_records = [
        point for point in available_records if point_values[point["id"]] is None
    ]
    point_balls = {
        point["id"]: exact_point_ball(point_values[point["id"]])
        for point in exact_records
    }
    abstract_metadata = {}
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for point in abstract_records:
        first_name, second_name = _producer_pair(point, drawable_values)
        groups[(point["origin"], first_name, second_name)].append(point)

    group_summaries = []
    for (origin, first_name, second_name), records in groups.items():
        first = drawable_values[first_name]
        second = drawable_values[second_name]
        if origin == "line_circle_residual":
            roots = line_circle_intersection_balls(
                (first.a, first.b, first.c),
                second,
            )
        elif origin == "circle_circle_residual":
            roots = circle_circle_intersection_balls(first, second)
        else:
            raise ValueError(f"未知抽象点来源: {origin}")

        materialized = [
            point
            for point in arrangement["points"]
            if point_values[point["id"]] is not None
            and first_name in point["incident_drawables"]
            and second_name in point["incident_drawables"]
        ]
        remaining = list(roots)
        for point in materialized:
            exact_ball = exact_point_ball(point_values[point["id"]])
            matches = [
                index
                for index, root in enumerate(remaining)
                if balls_may_overlap(root, exact_ball)
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"生产者 {first_name}/{second_name} 的已物化分支不能唯一匹配"
                )
            remaining.pop(matches[0])
        if len(remaining) != len(records):
            raise ValueError(
                f"生产者 {first_name}/{second_name} 的抽象分支数量不一致"
            )
        ordered_roots = sorted(
            remaining,
            key=lambda point: (
                float(point[0].center()),
                float(point[1].center()),
            ),
        )
        for record, root in zip(
            sorted(records, key=lambda item: item["id"]),
            ordered_roots,
        ):
            point_balls[record["id"]] = root
            abstract_metadata[record["id"]] = {
                "origin": origin,
                "producer": [first_name, second_name],
            }
        group_summaries.append(
            {
                "origin": origin,
                "producer": [first_name, second_name],
                "materialized_branches": len(materialized),
                "abstract_branches": len(records),
            }
        )

    ambiguous_pairs = []
    ordered_items = [
        (point["id"], point_balls[point["id"]]) for point in available_records
    ]
    for (first_id, first), (second_id, second) in combinations(ordered_items, 2):
        if balls_may_overlap(first, second):
            ambiguous_pairs.append([first_id, second_id])
            if len(ambiguous_pairs) >= 20:
                break
    if ambiguous_pairs:
        raise ValueError(f"46E 严格实球不能区分点: {ambiguous_pairs}")
    return {
        "available_records": available_records,
        "point_values": point_values,
        "drawable_values": drawable_values,
        "point_balls": point_balls,
        "abstract_metadata": abstract_metadata,
        "exact_points": len(exact_records),
        "abstract_points": len(abstract_records),
        "group_summaries": sorted(
            group_summaries,
            key=lambda item: (item["origin"], item["producer"]),
        ),
    }


def _abstract_point_on_line(
    point_id: str,
    target: Line,
    universe: dict,
) -> bool:
    metadata = universe["abstract_metadata"][point_id]
    first_name, second_name = metadata["producer"]
    first = universe["drawable_values"][first_name]
    second = universe["drawable_values"][second_name]
    if metadata["origin"] == "line_circle_residual":
        producer_line = first
        producer_circle = second
        if target == producer_line:
            return True
        point = _line_line_point(target, producer_line)
        if point is None or not producer_circle.contains(point):
            return False
    else:
        producer_circle = first
        axis = _radical_axis(first, second)
        if target == axis:
            return True
        point = _line_line_point(target, axis)
        if point is None or not producer_circle.contains(point):
            return False
    return balls_may_overlap(
        exact_point_ball(point),
        universe["point_balls"][point_id],
    )


def search_all_point_cross_tail_lines(
    certificate: dict,
    ga_ir: dict,
    source: dict,
    *,
    before_e: int = 46,
    trace=None,
) -> dict:
    """审计 36 条跨尾部根对弦线能否由两个 46E 安排点定义。"""

    if before_e != 46:
        raise ValueError("v1 报告冻结在 46E 状态")
    arrangement = build_runtime_arrangement(certificate, trace=trace)
    available_ids = _available_point_ids(ga_ir, before_e)
    universe = _materialize_available_balls(arrangement, available_ids)

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

    results = []
    interval_checks = 0
    interval_survivors = 0
    exact_coordinate_fallbacks = 0
    abstract_fallbacks = 0
    candidate_pairs = []
    for low_symbol in low_symbols:
        for high_symbol in high_symbols:
            target = Line.through(
                root_points[low_symbol],
                root_points[high_symbol],
            )
            ball_a = _real_ball(target.a)
            ball_b = _real_ball(target.b)
            ball_c = _real_ball(target.c)
            incident_points = []
            incident_exact = 0
            incident_abstract = 0
            for point_record in universe["available_records"]:
                point_id = point_record["id"]
                x, y = universe["point_balls"][point_id]
                residual = ball_a * x + ball_b * y + ball_c
                interval_checks += 1
                if not residual.contains_zero():
                    continue
                interval_survivors += 1
                point_value = universe["point_values"][point_id]
                if point_value is not None:
                    exact_coordinate_fallbacks += 1
                    on_line = target.contains(point_value)
                    if on_line:
                        incident_exact += 1
                else:
                    abstract_fallbacks += 1
                    on_line = _abstract_point_on_line(point_id, target, universe)
                    if on_line:
                        incident_abstract += 1
                if on_line:
                    incident_points.append(point_id)

            definitions = [
                [first, second]
                for first, second in combinations(incident_points, 2)
            ]
            existing_refs = [
                name
                for name, drawable in prefix_drawables
                if isinstance(drawable, Line) and drawable == target
            ]
            new_definition_count = 0 if existing_refs else len(definitions)
            result = {
                "low_symbol": low_symbol,
                "high_symbol": high_symbol,
                "incident_points": incident_points,
                "incident_exact_points": incident_exact,
                "incident_abstract_points": incident_abstract,
                "definitions": definitions,
                "definition_count": len(definitions),
                "new_definition_count": new_definition_count,
                "existing_drawable_references": existing_refs,
            }
            results.append(result)
            if new_definition_count:
                candidate_pairs.append([low_symbol, high_symbol])

    if len(results) != 36 or interval_checks != 36 * len(available_ids):
        raise AssertionError("完整点跨尾部直线审计覆盖数不一致")
    return {
        "schema": "euclid-min-tail-cross-pair-all-point-line-search/v1",
        "source": source,
        "semantics": {
            "state": "all_989_arrangement_points_available_after_46E",
            "candidate": "one_new_line_through_two_available_arrangement_points",
            "success": "line_intersects_encoding_circle_at_one_low_tail_and_one_high_tail_root",
            "exactness": "128_bit_strict_real_balls_with_exact_incidence_fallback",
        },
        "root_sets": {
            "low_tail": low_symbols,
            "high_tail": high_symbols,
        },
        "universe": {
            "available_points": len(available_ids),
            "exact_coordinate_points": universe["exact_points"],
            "abstract_residual_points": universe["abstract_points"],
            "abstract_producer_groups": universe["group_summaries"],
            "ambiguous_point_pairs": [],
        },
        "summary": {
            "cross_root_lines": len(results),
            "strict_ball_incidence_checks": interval_checks,
            "strict_ball_survivors": interval_survivors,
            "exact_coordinate_fallbacks": exact_coordinate_fallbacks,
            "abstract_incidence_fallbacks": abstract_fallbacks,
            "definitions_found": sum(
                result["definition_count"] for result in results
            ),
            "new_definitions_found": sum(
                result["new_definition_count"] for result in results
            ),
            "root_pairs_with_new_line": len(candidate_pairs),
        },
        "results": results,
        "candidate_root_pairs": candidate_pairs,
        "conclusion": {
            "status": "candidate_found" if candidate_pairs else "exhausted_no_candidate",
            "minimality_claim": "none",
        },
        "limitations": [
            "只审计一笔直线跨两个尾部直接产生根对，圆候选另行处理。",
            "不覆盖先加入一个新对象产生中间点、再用第二个对象联合产出的程序。",
            "空结果只排除该有限候选类，不证明两个尾部的 18E 最优。",
        ],
    }
