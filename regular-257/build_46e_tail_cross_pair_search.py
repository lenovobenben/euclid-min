"""生成 46E 具名前缀的跨尾部一笔联合产出搜索报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tail_cross_pair_search import search_cross_tail_direct_pairs


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
GADGET_PATH = ROOT / "geometry-gadgets-tail-69e.json"
OUTPUT_PATH = ROOT / "tail-cross-pair-direct-search-46e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    gadgets = json.loads(GADGET_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    ga_ir_sha256 = _sha256_file(GA_IR_PATH)
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    if gadgets["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("gadget 库对应的 GA-IR SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": ga_ir_sha256,
        "tail_gadget_library": GADGET_PATH.name,
        "tail_gadget_library_sha256": _sha256_file(GADGET_PATH),
    }
    return search_cross_tail_direct_pairs(certificate, ga_ir, source)


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
        f"prefix_named_points={summary['prefix_named_points']} "
        f"cross_root_pairs={summary['cross_root_pairs']}"
    )
    print(
        f"line_definitions_found={summary['line_definitions_found']} "
        f"circle_definitions_found={summary['circle_definitions_found']} "
        f"existing_redraws={summary['existing_redraw_definitions']} "
        f"new_definitions={summary['new_direct_definitions_found']} "
        f"pairs_with_direct_realization={summary['root_pairs_with_direct_realization']}"
    )
    print(f"status={report['conclusion']['status']}")


if __name__ == "__main__":
    main()
