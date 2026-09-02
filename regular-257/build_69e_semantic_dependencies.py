"""生成正 257 边形 69E 精确语义依赖超图报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from semantic_dependency import analyze_semantic_dependencies


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
VERIFICATION_PATH = ROOT / "verification-69e.json"
DEPENDENCY_PATH = ROOT / "dependency-graph-69e.json"
OUTPUT_PATH = ROOT / "semantic-dependencies-69e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    verification = json.loads(VERIFICATION_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    if not verification["valid"]:
        raise ValueError("语义依赖只能从验证通过的证书生成")
    if verification["certificate_sha256"] != certificate_sha256:
        raise ValueError("验证报告对应的证书 SHA-256 不一致")
    construction_sha256 = certificate["integrity"]["construction_sha256"]
    if verification["construction_sha256"] != construction_sha256:
        raise ValueError("验证报告对应的 construction SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "construction_sha256": construction_sha256,
        "verification_report": VERIFICATION_PATH.name,
        "dependency_report": DEPENDENCY_PATH.name,
        "dependency_report_sha256": _sha256_file(DEPENDENCY_PATH),
    }
    return analyze_semantic_dependencies(certificate, source)


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary = report["summary"]
    result = report["irreducibility_result"]
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"point_producer_hyperedges={summary['point_producer_hyperedges']} "
        f"drawable_definition_hyperedges={summary['drawable_definition_hyperedges']}"
    )
    print(
        "points_with_pre_use_alternatives="
        f"{summary['points_with_multiple_producers_before_first_paid_use']}"
    )
    print(
        "individually_removable_paid_draws="
        f"{summary['individually_removable_paid_draws']}"
    )
    print(
        "minimum_required_paid_draws_within_universe="
        f"{result['minimum_required_paid_draws_within_universe']}"
    )


if __name__ == "__main__":
    main()
