"""搜索 46E 具名前缀中能跨两个尾部一笔联合产生根对的直线或圆。"""

from __future__ import annotations

from itertools import combinations

from cyclotomic_replay import Circle, Line, Point, squared_distance
from geometry_algebra_ir import _algebra_system
from semantic_dependency import exact_replay_universe


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


def _existing_prefix_drawables(replay: dict, before_e: int) -> list[tuple[str, object]]:
    result = [("c0", replay["replayer"].names["c0"])]
    e_move = 0
    for entry in replay["paid_entries"]:
        e_move += 1
        if e_move > before_e:
            break
        result.append((entry["id"], replay["replayer"].names[entry["id"]]))
    return result


def search_cross_tail_direct_pairs(
    certificate: dict,
    ga_ir: dict,
    source: dict,
    *,
    before_e: int = 46,
) -> dict:
    """穷尽用两个具名前缀点定义的一笔直线/圆直接联合产出。"""

    if before_e != 46:
        raise ValueError("v1 报告冻结在两个尾部开始前的 46E 状态")
    replay = exact_replay_universe(certificate)
    replayer = replay["replayer"]
    prefix_points = [
        (name, point)
        for name, point in replay["point_items"]
        if replayer.bound_point_e_moves[name] <= before_e
    ]
    if len({point for _name, point in prefix_points}) != len(prefix_points):
        raise ValueError("46E 具名前缀含重合点，定义枚举需要先去重")
    prefix_drawables = _existing_prefix_drawables(replay, before_e)

    _symbols, _relations, values = _algebra_system()
    low_symbols = _macro(ga_ir, "macro.low-tail")["output_symbols"]
    high_symbols = _macro(ga_ir, "macro.high-tail")["output_symbols"]
    root_points = {
        symbol_id: _encoded_point(values[symbol_id])
        for symbol_id in [*low_symbols, *high_symbols]
    }

    results = []
    pair_hits = []
    total_line_definitions = 0
    total_circle_definitions = 0
    existing_redraw_definitions = 0
    distinct_new_lines = set()
    distinct_new_circles = set()
    for low_symbol in low_symbols:
        for high_symbol in high_symbols:
            low_point = root_points[low_symbol]
            high_point = root_points[high_symbol]
            if low_point == high_point:
                raise ValueError(f"跨尾部根意外重合: {low_symbol} = {high_symbol}")

            target_line = Line.through(low_point, high_point)
            incident_prefix_points = [
                name for name, point in prefix_points if target_line.contains(point)
            ]
            line_definitions = [
                [first, second]
                for first, second in combinations(incident_prefix_points, 2)
            ]
            existing_line_refs = [
                name
                for name, drawable in prefix_drawables
                if isinstance(drawable, Line) and drawable == target_line
            ]
            total_line_definitions += len(line_definitions)
            new_line_definition_count = (
                0 if existing_line_refs else len(line_definitions)
            )
            if existing_line_refs:
                existing_redraw_definitions += len(line_definitions)
            if line_definitions and not existing_line_refs:
                distinct_new_lines.add((low_symbol, high_symbol))

            circle_candidates = []
            for center_name, center in prefix_points:
                radius_squared = squared_distance(center, low_point)
                if radius_squared == 0 or squared_distance(center, high_point) != radius_squared:
                    continue
                through_points = [
                    name
                    for name, point in prefix_points
                    if name != center_name
                    and squared_distance(center, point) == radius_squared
                ]
                if not through_points:
                    continue
                candidate = Circle(center, radius_squared)
                existing_circle_refs = [
                    name
                    for name, drawable in prefix_drawables
                    if isinstance(drawable, Circle) and drawable == candidate
                ]
                circle_candidates.append(
                    {
                        "center": center_name,
                        "through_points": through_points,
                        "definition_count": len(through_points),
                        "new_definition_count": (
                            0 if existing_circle_refs else len(through_points)
                        ),
                        "existing_drawable_references": existing_circle_refs,
                    }
                )
                total_circle_definitions += len(through_points)
                if existing_circle_refs:
                    existing_redraw_definitions += len(through_points)
                if not existing_circle_refs:
                    distinct_new_circles.add((low_symbol, high_symbol, center_name))

            new_circle_definition_count = sum(
                candidate["new_definition_count"] for candidate in circle_candidates
            )
            direct_count = new_line_definition_count + new_circle_definition_count
            result = {
                "low_symbol": low_symbol,
                "high_symbol": high_symbol,
                "line": {
                    "incident_prefix_points": incident_prefix_points,
                    "definitions": line_definitions,
                    "definition_count": len(line_definitions),
                    "new_definition_count": new_line_definition_count,
                    "existing_drawable_references": existing_line_refs,
                },
                "circles": circle_candidates,
                "circle_definition_count": sum(
                    candidate["definition_count"] for candidate in circle_candidates
                ),
                "new_circle_definition_count": new_circle_definition_count,
                "new_direct_definition_count": direct_count,
            }
            results.append(result)
            if direct_count:
                pair_hits.append([low_symbol, high_symbol])

    expected_pairs = len(low_symbols) * len(high_symbols)
    if len(results) != expected_pairs:
        raise AssertionError("跨尾部根对没有完整枚举")
    return {
        "schema": "euclid-min-tail-cross-pair-direct-search/v1",
        "source": source,
        "semantics": {
            "state": "all_named_points_and_paid_drawables_available_after_46E",
            "candidate": "one_new_line_or_circle_defined_only_by_two_named_prefix_points",
            "success": "candidate_intersects_encoding_circle_at_one_low_tail_and_one_high_tail_root",
            "geometry": "exact_cyclotomic_incidence_without_float_tolerance",
        },
        "root_sets": {
            "low_tail": low_symbols,
            "high_tail": high_symbols,
        },
        "summary": {
            "prefix_named_points": len(prefix_points),
            "prefix_drawables": len(prefix_drawables),
            "cross_root_pairs": expected_pairs,
            "line_definitions_found": total_line_definitions,
            "circle_definitions_found": total_circle_definitions,
            "existing_redraw_definitions": existing_redraw_definitions,
            "new_direct_definitions_found": (
                total_line_definitions
                + total_circle_definitions
                - existing_redraw_definitions
            ),
            "distinct_new_line_geometries_found": len(distinct_new_lines),
            "distinct_new_circle_geometries_found": len(distinct_new_circles),
            "root_pairs_with_direct_realization": len(pair_hits),
        },
        "results": results,
        "root_pair_hits": pair_hits,
        "conclusion": {
            "status": "candidate_found" if pair_hits else "exhausted_no_candidate",
            "minimality_claim": "none",
        },
        "limitations": [
            "只允许使用 46E 时已经具名的点定义新对象，尚未使用可用的未命名安排点。",
            "只检查一笔对象直接同时产生一个低尾部根和一个高尾部根，不覆盖多笔联合程序。",
            "空结果只排除该有限候选类，不证明两个尾部的 18E 最优。",
        ],
    }
