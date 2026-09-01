"""汇总 M257-8 最大前沿全部可用点的单个最终对象搜索。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POINT_AUDIT_PATH = ROOT / "residual-point-ball-audit-68e.json"
LINE_CHORD_PATH = ROOT / "all-point-line-chord-search-68e.json"
LINE_ADJACENT_PATH = ROOT / "all-point-line-adjacent-search-68e.json"
CIRCLE_PATH = ROOT / "all-point-circle-search-68e.json"
OUTPUT_PATH = ROOT / "all-point-direct-search-68e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report() -> dict:
    point_audit = _load(POINT_AUDIT_PATH)
    line_chord = _load(LINE_CHORD_PATH)
    line_adjacent = _load(LINE_ADJACENT_PATH)
    circle = _load(CIRCLE_PATH)
    reports = (line_chord, line_adjacent, circle)
    if point_audit["audit"]["status"] != "complete":
        raise ValueError("全部点搜索依赖的残余点实球审计尚未完成")
    if any(report["search"]["unresolved_count"] != 0 for report in reports):
        raise ValueError("全部点搜索仍有未决定义")
    if any(report["search"]["solutions_found"] != 0 for report in reports):
        raise ValueError("全部点搜索中存在候选解")
    if any(
        report["search"]["status"] != "exhausted_no_solution"
        for report in reports
    ):
        raise ValueError("全部点搜索尚未穷尽")

    available_points = point_audit["universe"]["available_points"]
    line_definitions = available_points * (available_points - 1) // 2
    circle_definitions = available_points * (available_points - 1)
    if line_chord["universe"]["line_definitions"] != line_definitions:
        raise ValueError("全部点目标弦直线定义数不一致")
    if line_adjacent["universe"]["line_definitions"] != line_definitions:
        raise ValueError("全部点邻接直线定义数不一致")
    if circle["universe"]["circle_definitions"] != circle_definitions:
        raise ValueError("全部点圆定义数不一致")

    return {
        "schema": "euclid-min-regular-257-all-point-direct-search/v1",
        "source": {
            "residual_point_ball_audit": POINT_AUDIT_PATH.name,
            "residual_point_ball_audit_sha256": _sha256_file(POINT_AUDIT_PATH),
            "line_chord_report": LINE_CHORD_PATH.name,
            "line_chord_report_sha256": _sha256_file(LINE_CHORD_PATH),
            "line_adjacent_report": LINE_ADJACENT_PATH.name,
            "line_adjacent_report_sha256": _sha256_file(LINE_ADJACENT_PATH),
            "circle_report": CIRCLE_PATH.name,
            "circle_report_sha256": _sha256_file(CIRCLE_PATH),
        },
        "semantics": {
            "removed_paid_drawables": ["BG0", "target_transfer"],
            "selected_paid_drawables": 67,
            "candidate_e_move": 68,
            "candidate_definition_points": "all_available_arrangement_points",
            "covered_candidate_families": [
                "line_through_two_distinct_definition_points",
                "circle_with_distinct_center_and_through_definition_points",
            ],
            "exhaustive_target_events": [
                "the_two_new_intersections_of_candidate_and_c0_are_adjacent",
                "a_new_candidate_intersection_on_c0_is_adjacent_to_an_"
                "already_available_point_on_c0",
            ],
            "completeness_argument": (
                "加入候选前尚无目标边；候选是最后一个付费对象，所以首次目标边必含至少"
                "一个候选与目标圆的新交点。另一端只能是另一个新交点或既有目标圆点。"
            ),
            "strictness": (
                "全部否定项均由严格实球区间证明；仅有的区间未决项由安排关联表精确确认"
                "为以 C 为圆心重画目标圆，因而不产生新交点。"
            ),
            "limitations": [
                "结论只覆盖删除第 68、69 步的最大前沿，不覆盖其余 2345 个删二状态。",
                "结论只允许加入一个作为最后第 68E 的新对象，不是 69E 的全局下界。",
            ],
        },
        "universe": {
            "available_points": available_points,
            "exact_coordinate_points": point_audit["universe"][
                "materialized_exact_points"
            ],
            "strict_ball_residual_points": point_audit["universe"][
                "materialized_residual_points"
            ],
            "line_definitions": line_definitions,
            "circle_definitions": circle_definitions,
            "drawable_definitions": line_definitions + circle_definitions,
        },
        "search": {
            "line_chord_definitions_tested": line_chord["search"][
                "definitions_tested"
            ],
            "line_adjacent_definitions_tested": line_adjacent["search"][
                "definitions_tested"
            ],
            "line_adjacent_relation_checks": line_adjacent["search"][
                "ball_relation_checks"
            ],
            "circle_definitions_tested": circle["search"]["definitions_tested"],
            "circle_relation_checks": circle["search"]["ball_relation_checks"],
            "redrawn_target_circle_definitions": circle["search"][
                "redrawn_target_circle_count"
            ],
            "unresolved_definitions": 0,
            "solutions_found": 0,
            "status": "exhausted_no_solution_in_all_point_maximum_frontier",
        },
        "conclusion": (
            "在删除 BG0 与 target_transfer、保留前 67E 的最大前沿中，以任意两个可用"
            "安排点定义一条直线，或以任意一对不同的可用安排点定义圆心和圆上一点，都"
            "不能作为最后的第 68E 直接产生正 257 边形的一条边。"
        ),
    }


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote={OUTPUT_PATH}")
    print(f"drawable_definitions={report['universe']['drawable_definitions']}")
    print(f"status={report['search']['status']}")


if __name__ == "__main__":
    main()
