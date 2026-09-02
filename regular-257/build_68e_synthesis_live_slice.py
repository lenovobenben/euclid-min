"""生成面向正 257 边形 68E 合成的活跃接口报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from algebra_live_slice import build_synthesis_live_slice


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
GADGET_LIBRARY_PATH = ROOT / "geometry-gadgets-tail-69e.json"
OUTPUT_PATH = ROOT / "synthesis-live-slice-68e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    gadgets = json.loads(GADGET_LIBRARY_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    ga_ir_sha256 = _sha256_file(GA_IR_PATH)
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    if gadgets["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("gadget 库对应的证书 SHA-256 不一致")
    if gadgets["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("gadget 库对应的 GA-IR SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "construction_sha256": certificate["integrity"]["construction_sha256"],
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": ga_ir_sha256,
        "geometry_gadget_library": GADGET_LIBRARY_PATH.name,
        "geometry_gadget_library_sha256": _sha256_file(GADGET_LIBRARY_PATH),
    }
    return build_synthesis_live_slice(certificate, ga_ir, gadgets, source)


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    algebra = report["algebraic_slice"]["summary"]
    contract = report["synthesis_contract"]
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"roots={algebra['demanded_quadratic_roots']}/"
        f"{algebra['quadratic_roots_total']} "
        f"byproducts={algebra['free_sibling_byproduct_roots']} "
        f"relations={algebra['active_relations']}/{algebra['relations_total']}"
    )
    print(
        f"tail_outputs={','.join(contract['required_output_symbols'])} "
        f"baseline={contract['baseline_contextual_cost_e']}E "
        f"target<={contract['maximum_candidate_contextual_cost_e']}E"
    )


if __name__ == "__main__":
    main()
