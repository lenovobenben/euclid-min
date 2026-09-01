"""用 46E 完整点闭包审计跨尾部根对的一笔圆联合产出。"""

from __future__ import annotations

from cyclotomic_replay import Circle, Line
from full_intersection_closure import build_runtime_arrangement
from geometry_algebra_ir import _algebra_system
from residual_point_ball_audit import _real_ball
from tail_cross_pair_all_point_line_search import (
    _abstract_point_on_line,
    _available_point_ids,
    _encoded_point,
    _macro,
    _materialize_available_balls,
)


def _perpendicular_bisector(first, second) -> Line:
    return Line(
        2 * (second.x - first.x),
        2 * (second.y - first.y),
        first.x * first.x
        + first.y * first.y
        - second.x * second.x
        - second.y * second.y,
    )


def search_all_point_cross_tail_circles(
    certificate: dict,
    ga_ir: dict,
    source: dict,
    *,
    before_e: int = 46,
    trace=None,
) -> dict:
    """审计由两个 46E 安排点定义、同时经过跨尾部根对的圆。"""

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
    prefix_circles = [
        ("c0", universe["drawable_values"]["c0"]),
        *[
            (drawable["id"], universe["drawable_values"][drawable["id"]])
            for drawable in arrangement["drawables"]
            if drawable["e_move"] <= before_e
            and isinstance(universe["drawable_values"][drawable["id"]], Circle)
        ],
    ]

    results = []
    center_checks = 0
    strict_ball_survivors = 0
    exact_center_fallbacks = 0
    abstract_center_fallbacks = 0
    candidate_pairs = []
    for low_symbol in low_symbols:
        for high_symbol in high_symbols:
            low_point = root_points[low_symbol]
            high_point = root_points[high_symbol]
            bisector = _perpendicular_bisector(low_point, high_point)
            ball_a = _real_ball(bisector.a)
            ball_b = _real_ball(bisector.b)
            ball_c = _real_ball(bisector.c)
            center_points = []
            exact_centers = []
            abstract_centers = []
            existing_circle_centers = []
            new_exact_centers = []
            new_abstract_centers = []
            for point_record in universe["available_records"]:
                point_id = point_record["id"]
                x, y = universe["point_balls"][point_id]
                residual = ball_a * x + ball_b * y + ball_c
                center_checks += 1
                if not residual.contains_zero():
                    continue
                strict_ball_survivors += 1
                point_value = universe["point_values"][point_id]
                if point_value is not None:
                    exact_center_fallbacks += 1
                    on_bisector = bisector.contains(point_value)
                else:
                    abstract_center_fallbacks += 1
                    on_bisector = _abstract_point_on_line(
                        point_id,
                        bisector,
                        universe,
                    )
                if not on_bisector:
                    continue
                center_points.append(point_id)
                if point_value is None:
                    abstract_centers.append(point_id)
                    new_abstract_centers.append(point_id)
                    continue
                exact_centers.append(point_id)
                candidate_circle = Circle.through(point_value, low_point)
                if not candidate_circle.contains(high_point):
                    raise AssertionError("垂直平分线圆心没有同时经过两个根")
                existing_refs = [
                    name
                    for name, circle in prefix_circles
                    if circle == candidate_circle
                ]
                if existing_refs:
                    existing_circle_centers.append(
                        {
                            "center": point_id,
                            "existing_drawable_references": existing_refs,
                        }
                    )
                else:
                    new_exact_centers.append(point_id)

            unresolved_centers = [*new_exact_centers, *new_abstract_centers]
            result = {
                "low_symbol": low_symbol,
                "high_symbol": high_symbol,
                "center_points": center_points,
                "exact_center_points": exact_centers,
                "abstract_center_points": abstract_centers,
                "existing_circle_centers": existing_circle_centers,
                "new_exact_center_points": new_exact_centers,
                "new_abstract_center_points": new_abstract_centers,
                "unresolved_new_center_count": len(unresolved_centers),
            }
            results.append(result)
            if unresolved_centers:
                candidate_pairs.append([low_symbol, high_symbol])

    if len(results) != 36 or center_checks != 36 * len(available_ids):
        raise AssertionError("完整点跨尾部圆心审计覆盖数不一致")
    unresolved = bool(candidate_pairs)
    return {
        "schema": "euclid-min-tail-cross-pair-all-point-circle-search/v1",
        "source": source,
        "semantics": {
            "state": "all_989_arrangement_points_available_after_46E",
            "candidate": "one_new_circle_with_available_center_and_available_through_point",
            "necessary_center_condition": "center_lies_on_perpendicular_bisector_of_cross_tail_root_pair",
            "exactness": "128_bit_strict_real_balls_with_exact_incidence_and_geometry_identity_fallback",
        },
        "root_sets": {
            "low_tail": low_symbols,
            "high_tail": high_symbols,
        },
        "universe": {
            "available_points": len(available_ids),
            "exact_coordinate_points": universe["exact_points"],
            "abstract_residual_points": universe["abstract_points"],
            "ambiguous_point_pairs": [],
        },
        "summary": {
            "cross_root_pairs": len(results),
            "strict_ball_center_checks": center_checks,
            "strict_ball_survivors": strict_ball_survivors,
            "exact_center_fallbacks": exact_center_fallbacks,
            "abstract_center_fallbacks": abstract_center_fallbacks,
            "center_incidences": sum(len(result["center_points"]) for result in results),
            "existing_circle_center_incidences": sum(
                len(result["existing_circle_centers"]) for result in results
            ),
            "new_exact_center_incidences": sum(
                len(result["new_exact_center_points"]) for result in results
            ),
            "new_abstract_center_incidences": sum(
                len(result["new_abstract_center_points"]) for result in results
            ),
            "root_pairs_requiring_through_point_audit": len(candidate_pairs),
        },
        "results": results,
        "candidate_root_pairs": candidate_pairs,
        "conclusion": {
            "status": (
                "requires_through_point_audit"
                if unresolved
                else "exhausted_no_new_circle_center"
            ),
            "minimality_claim": "none",
        },
        "limitations": [
            "若发现新圆心，还必须继续证明存在同半径的可用圆上点；本报告不会把圆心条件误当充分条件。",
            "只审计一笔圆跨两个尾部直接产生根对，不覆盖两笔或更多新对象的联合程序。",
            "空结果只排除该有限候选类，不证明两个尾部的 18E 最优。",
        ],
    }
