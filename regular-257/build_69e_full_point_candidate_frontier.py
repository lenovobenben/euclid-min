"""生成 M257-8 完整交点删二候选前沿报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from full_point_candidate_frontier import analyze_candidate_frontier


ROOT = Path(__file__).resolve().parent
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
OUTPUT_PATH = ROOT / "full-point-candidate-frontier-69e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    full_report = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    if not full_report["irreducibility_result"][
        "all_paid_draws_individually_necessary"
    ]:
        raise ValueError("候选前沿必须建立在 M257-6 完整交点审计之上")
    source = {
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(
            FULL_CLOSURE_PATH
        ),
    }
    return analyze_candidate_frontier(full_report, source)


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    inventory = report["inventory"]
    summary = report["summary"]
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"exact_coordinate_points={inventory['exact_coordinate_points']} "
        f"abstract_residual_points={inventory['abstract_residual_points']}"
    )
    print(
        "available_exact_coordinate_points="
        f"{summary['minimum_available_exact_coordinate_points']}.."
        f"{summary['maximum_available_exact_coordinate_points']}"
    )
    print(
        "trials_reaching_target_before_candidate="
        f"{summary['trials_reaching_target_before_candidate']}"
    )


if __name__ == "__main__":
    main()
