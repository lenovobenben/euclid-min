"""生成 46E 完整点闭包的跨尾部一笔直线搜索报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tail_cross_pair_all_point_line_search import search_all_point_cross_tail_lines


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
NAMED_SEARCH_PATH = ROOT / "tail-cross-pair-direct-search-46e.json"
OUTPUT_PATH = ROOT / "tail-cross-pair-all-point-line-search-46e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(*, trace: bool = False) -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    full_closure = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    named_search = json.loads(NAMED_SEARCH_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    ga_ir_sha256 = _sha256_file(GA_IR_PATH)
    if full_closure["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("完整交点闭包对应的证书 SHA-256 不一致")
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    if named_search["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("具名点搜索对应的 GA-IR SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(FULL_CLOSURE_PATH),
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": ga_ir_sha256,
        "named_prefix_search": NAMED_SEARCH_PATH.name,
        "named_prefix_search_sha256": _sha256_file(NAMED_SEARCH_PATH),
    }
    tracer = (lambda message: print(message, flush=True)) if trace else None
    return search_all_point_cross_tail_lines(
        certificate,
        ga_ir,
        source,
        trace=tracer,
    )


def main() -> None:
    report = build_report(trace=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    universe = report["universe"]
    summary = report["summary"]
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"available_points={universe['available_points']} "
        f"exact={universe['exact_coordinate_points']} "
        f"abstract={universe['abstract_residual_points']}"
    )
    print(
        f"incidence_checks={summary['strict_ball_incidence_checks']} "
        f"survivors={summary['strict_ball_survivors']} "
        f"new_definitions={summary['new_definitions_found']}"
    )
    print(f"status={report['conclusion']['status']}")


if __name__ == "__main__":
    main()
