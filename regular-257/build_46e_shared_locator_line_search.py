"""生成 46E 状态中跨根载线共享定位点的新直线搜索报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from shared_locator_line_search import search_shared_locator_lines


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
CHORD_IR_PATH = ROOT / "tail-quadratic-chord-ir-68e.json"
OUTPUT_PATH = ROOT / "shared-locator-line-search-46e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(*, trace: bool = False) -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    full_closure = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    chord_ir = json.loads(CHORD_IR_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    ga_ir_sha256 = _sha256_file(GA_IR_PATH)
    if full_closure["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("完整闭包对应的证书 SHA-256 不一致")
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    if chord_ir["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("根载线 IR 对应的 GA-IR SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "construction_sha256": certificate["integrity"]["construction_sha256"],
        "full_intersection_closure": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_sha256": _sha256_file(FULL_CLOSURE_PATH),
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": ga_ir_sha256,
        "tail_quadratic_chord_ir": CHORD_IR_PATH.name,
        "tail_quadratic_chord_ir_sha256": _sha256_file(CHORD_IR_PATH),
    }
    tracer = (lambda message: print(message, flush=True)) if trace else None
    return search_shared_locator_lines(
        certificate,
        ga_ir,
        chord_ir,
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
        f"space={summary['bridge_pair_space']} "
        f"constructible_lines={summary['constructible_new_lines']} "
        f"constructible={summary['distinct_constructible_new_lines']} "
        f"shared={summary['shared_new_locator_lines']}"
    )
    print(f"status={report['conclusion']['status']}")


if __name__ == "__main__":
    main()
