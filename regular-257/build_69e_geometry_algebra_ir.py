"""生成正 257 边形 69E 几何—代数统一基线 IR。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from geometry_algebra_ir import build_geometry_algebra_ir


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
OUTPUT_PATH = ROOT / "geometry-algebra-baseline-69e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    full_report = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    if full_report["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("完整交点闭包对应的证书 SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "construction_sha256": certificate["integrity"]["construction_sha256"],
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(FULL_CLOSURE_PATH),
    }
    return build_geometry_algebra_ir(certificate, full_report, source)


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit = report["cost_audit"]
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"cost={audit['construction_cost_e']}E "
        f"relations={len(report['algebraic_relations'])} "
        f"representations={len(report['representations'])}"
    )
    print(
        "free_points="
        f"{audit['free_points_born_after_paid_transitions']} "
        "early_named_bindings="
        f"{audit['named_bindings_available_earlier']}"
    )


if __name__ == "__main__":
    main()
