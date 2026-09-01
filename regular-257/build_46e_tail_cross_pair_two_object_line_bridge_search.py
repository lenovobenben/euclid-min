"""生成 46E 完整点闭包的跨尾部两对象目标直线桥接报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tail_cross_pair_two_object_line_bridge_search import (
    search_two_object_line_bridges,
)


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
ALL_POINT_LINE_PATH = ROOT / "tail-cross-pair-all-point-line-search-46e.json"
ALL_POINT_CIRCLE_PATH = ROOT / "tail-cross-pair-all-point-circle-search-46e.json"
OUTPUT_PATH = ROOT / "tail-cross-pair-two-object-line-bridge-search-46e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(*, trace: bool = False) -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    full_closure = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    all_point_line = json.loads(ALL_POINT_LINE_PATH.read_text(encoding="utf-8"))
    all_point_circle = json.loads(ALL_POINT_CIRCLE_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    ga_ir_sha256 = _sha256_file(GA_IR_PATH)
    if full_closure["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("完整交点闭包对应的证书 SHA-256 不一致")
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    if all_point_line["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("完整点直线搜索对应的 GA-IR SHA-256 不一致")
    if all_point_circle["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("完整点圆搜索对应的 GA-IR SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(FULL_CLOSURE_PATH),
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": ga_ir_sha256,
        "all_point_line_search": ALL_POINT_LINE_PATH.name,
        "all_point_line_search_sha256": _sha256_file(ALL_POINT_LINE_PATH),
        "all_point_circle_search": ALL_POINT_CIRCLE_PATH.name,
        "all_point_circle_search_sha256": _sha256_file(ALL_POINT_CIRCLE_PATH),
    }
    tracer = (lambda message: print(message, flush=True)) if trace else None
    return search_two_object_line_bridges(
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
    summary = report["summary"]
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"pair_space={summary['center_bridge_pair_space']} "
        f"overlaps={summary['strict_radius_overlap_survivors']} "
        f"exact={summary['exact_radius_equalities']}"
    )
    print(
        f"new_circles={summary['new_circle_geometries']} "
        f"drawable={summary['drawable_new_circle_candidates']} "
        f"root_pairs={summary['root_pairs_with_2e_bridge']}"
    )
    print(f"status={report['conclusion']['status']}")


if __name__ == "__main__":
    main()
