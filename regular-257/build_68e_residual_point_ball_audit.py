"""生成 M257-8 最大前沿抽象残余点的严格实球审计报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from residual_point_ball_audit import (
    BALL_PRECISION,
    prepare_maximum_frontier_ball_universe,
    serialize_ball_point,
)


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
FRONTIER_PATH = ROOT / "full-point-candidate-frontier-69e.json"
CACHE_PATH = ROOT / "tmp" / "m257-8-final-pair-all-point-balls.json"
OUTPUT_PATH = ROOT / "residual-point-ball-audit-68e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def build_report(trace=None) -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    frontier = json.loads(FRONTIER_PATH.read_text(encoding="utf-8"))
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": _sha256_file(CERTIFICATE_PATH),
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(FULL_CLOSURE_PATH),
        "candidate_frontier_report": FRONTIER_PATH.name,
        "candidate_frontier_report_sha256": _sha256_file(FRONTIER_PATH),
    }
    universe = prepare_maximum_frontier_ball_universe(
        certificate,
        frontier,
        trace=trace,
    )
    cache = {
        "schema": "euclid-min-regular-257-all-point-ball-cache/v1",
        "source": source,
        "precision_bits": BALL_PRECISION,
        "point_ids": [name for name, _ball in universe["point_items"]],
        "balls": [
            serialize_ball_point(ball) for _name, ball in universe["point_items"]
        ],
    }
    _write_json_atomic(CACHE_PATH, cache)
    producer_groups = universe["producer_groups"]
    report = {
        "schema": "euclid-min-regular-257-residual-point-ball-audit/v1",
        "source": source,
        "semantics": {
            "removed_paid_drawables": universe["removed"],
            "purpose": (
                "用严格实球物化最大前沿中尚无分圆域坐标的残余交点，并证明全部可用点"
                "在当前精度下可区分。"
            ),
            "limitations": [
                "实球给出严格包围和否定判定；若后续候选关系区间包含 0，仍须回退到精确代数判定。",
                "本报告只处理删除第 68、69 步的最大前沿。",
            ],
        },
        "precision_bits": BALL_PRECISION,
        "universe": {
            "available_points": universe["available_points"],
            "materialized_exact_points": universe["exact_points"],
            "materialized_residual_points": universe["abstract_points"],
            "line_circle_residual_points": universe["abstract_origin_counts"][
                "line_circle_residual"
            ],
            "circle_circle_residual_points": universe["abstract_origin_counts"][
                "circle_circle_residual"
            ],
            "residual_producer_groups": len(producer_groups),
        },
        "audit": {
            "incidence_checks": universe["incidence_checks"],
            "failed_incidences": universe["failed_incidences"],
            "ambiguous_point_pairs": universe["ambiguous_point_pairs"],
            "all_residual_points_materialized": (
                universe["abstract_points"]
                == sum(
                    group["residual_branches"] for group in producer_groups
                )
            ),
            "all_incidences_enclosed": not universe["failed_incidences"],
            "all_available_points_separated": not universe[
                "ambiguous_point_pairs"
            ],
            "status": (
                "complete"
                if not universe["failed_incidences"]
                and not universe["ambiguous_point_pairs"]
                else "needs_higher_precision_or_exact_resolution"
            ),
        },
    }
    return report


def main() -> None:
    report = build_report(trace=lambda message: print(message, flush=True))
    _write_json_atomic(OUTPUT_PATH, report)
    print(f"wrote={OUTPUT_PATH}")
    print(f"cache={CACHE_PATH}")
    print(f"status={report['audit']['status']}")


if __name__ == "__main__":
    main()
