"""生成 68E 合成器使用的尾部二次根载线 IR。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from quadratic_chord_ir import build_tail_quadratic_chord_ir


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
LIVE_SLICE_PATH = ROOT / "synthesis-live-slice-68e.json"
OUTPUT_PATH = ROOT / "tail-quadratic-chord-ir-68e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    full_report = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    live_slice = json.loads(LIVE_SLICE_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    ga_ir_sha256 = _sha256_file(GA_IR_PATH)
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    if full_report["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("完整闭包对应的证书 SHA-256 不一致")
    if live_slice["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("活跃切片对应的 GA-IR SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "construction_sha256": certificate["integrity"]["construction_sha256"],
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": ga_ir_sha256,
        "full_intersection_closure": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_sha256": _sha256_file(FULL_CLOSURE_PATH),
        "synthesis_live_slice": LIVE_SLICE_PATH.name,
        "synthesis_live_slice_sha256": _sha256_file(LIVE_SLICE_PATH),
    }
    return build_tail_quadratic_chord_ir(
        certificate,
        ga_ir,
        full_report,
        live_slice,
        source,
    )


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary = report["summary"]
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"tasks={summary['tail_relation_tasks']} "
        f"verified={summary['formula_lines_equal_baseline_carriers']} "
        f"prefix_incident={summary['tasks_with_any_available_incident_point_at_46e']} "
        f"prefix_drawable={summary['tasks_with_two_available_incident_points_at_46e']}"
    )


if __name__ == "__main__":
    main()
