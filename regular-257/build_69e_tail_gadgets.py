"""生成正 257 边形两个 9E 尾部的可执行 gadget 基线。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from geometry_gadget import build_tail_gadget_library


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
OUTPUT_PATH = ROOT / "geometry-gadgets-tail-69e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "construction_sha256": certificate["integrity"]["construction_sha256"],
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": _sha256_file(GA_IR_PATH),
    }
    return build_tail_gadget_library(certificate, ga_ir, source)


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote={OUTPUT_PATH}")
    for gadget in report["gadgets"]:
        closure = gadget["effects"]["full_free_closure_delta"]
        print(
            f"{gadget['id']}: cost={gadget['cost']['e_move']}E "
            f"program_entries={len(gadget['program'])} "
            f"free_points={closure['point_count']}"
        )
    comparison = report["comparison"]
    print(
        f"combined={comparison['baseline_combined_cost_e']}E "
        f"shared_points={len(comparison['shared_required_points'])} "
        f"shared_drawables={len(comparison['shared_required_drawables'])}"
    )


if __name__ == "__main__":
    main()
