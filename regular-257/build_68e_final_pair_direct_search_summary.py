"""汇总 M257-8 最大前沿中单个最终对象的完整搜索结果。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTIER_PATH = ROOT / "full-point-candidate-frontier-69e.json"
LINE_CHORD_PATH = ROOT / "final-pair-line-chord-search-68e.json"
LINE_ADJACENT_PATH = ROOT / "final-pair-line-adjacent-search-68e.json"
CIRCLE_PATH = ROOT / "final-pair-circle-search-68e.json"
OUTPUT_PATH = ROOT / "final-pair-direct-search-68e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report() -> dict:
    frontier = _load(FRONTIER_PATH)
    line_chord = _load(LINE_CHORD_PATH)
    line_adjacent = _load(LINE_ADJACENT_PATH)
    circle = _load(CIRCLE_PATH)

    maximum = frontier["summary"]["maximum_frontier_trials"][0]
    if maximum["removed"] != ["BG0", "target_transfer"]:
        raise ValueError("最大前沿的删除对象与搜索分片不一致")
    reports = (line_chord, line_adjacent, circle)
    if any(report["search"]["solutions_found"] != 0 for report in reports):
        raise ValueError("单个最终对象搜索中存在候选解，不能生成空结果汇总")
    if any(
        report["search"]["status"] != "exhausted_no_solution"
        for report in reports
    ):
        raise ValueError("存在尚未穷尽的单个最终对象搜索")

    exact_points = maximum["available_exact_coordinate_points"]
    available_points = maximum["available_points"]
    line_definitions = exact_points * (exact_points - 1) // 2
    circle_definitions = exact_points * (exact_points - 1)
    if line_chord["universe"]["line_definitions"] != line_definitions:
        raise ValueError("直线目标弦报告的定义数不一致")
    if line_adjacent["universe"]["line_definitions"] != line_definitions:
        raise ValueError("直线既有点邻接报告的定义数不一致")
    if circle["universe"]["circle_definitions"] != circle_definitions:
        raise ValueError("圆报告的定义数不一致")

    return {
        "schema": "euclid-min-regular-257-final-pair-direct-search/v1",
        "source": {
            "candidate_frontier_report": FRONTIER_PATH.name,
            "candidate_frontier_report_sha256": _sha256_file(FRONTIER_PATH),
            "line_chord_report": LINE_CHORD_PATH.name,
            "line_chord_report_sha256": _sha256_file(LINE_CHORD_PATH),
            "line_adjacent_report": LINE_ADJACENT_PATH.name,
            "line_adjacent_report_sha256": _sha256_file(LINE_ADJACENT_PATH),
            "circle_report": CIRCLE_PATH.name,
            "circle_report_sha256": _sha256_file(CIRCLE_PATH),
        },
        "semantics": {
            "removed_paid_drawables": maximum["removed"],
            "selected_paid_drawables": maximum["available_paid_drawables"],
            "candidate_e_move": 68,
            "candidate_definition_points": (
                "available_points_with_materialized_exact_coordinates"
            ),
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
                "加入候选前尚无目标边；候选是最后一个付费对象，所以首次出现的目标边"
                "必含至少一个候选与目标圆的新交点。其另一端只能是另一个新交点，或加入"
                "候选前已经可用的目标圆点。"
            ),
            "limitations": [
                "最大前沿的 2103 个可用点中，344 个抽象圆交点尚无精确坐标，未作为候选定义点。",
                "结论只覆盖删除第 68、69 步的最大前沿，不覆盖其余 2345 个删二状态。",
            ],
        },
        "universe": {
            "available_points": available_points,
            "available_exact_coordinate_points": exact_points,
            "available_abstract_residual_points": available_points - exact_points,
            "global_abstract_residual_points": frontier["inventory"][
                "abstract_residual_points"
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
            "circle_definitions_tested": circle["search"]["definitions_tested"],
            "circle_exact_fallbacks": circle["search"]["exact_checks"],
            "solutions_found": 0,
            "status": "exhausted_no_solution_in_materialized_exact_maximum_frontier",
        },
        "conclusion": (
            "在删除 BG0 与 target_transfer、保留前 67E 的最大前沿中，以任意两个已物化"
            "精确点定义一条直线，或以任意一对不同的已物化精确点定义圆心和圆上一点，"
            "都不能作为最后的第 68E 直接产生正 257 边形的一条边。"
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
