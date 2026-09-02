"""生成正 257 边形 69E 证书的依赖图报告。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dependency_graph import analyze_dependency_graph, render_paid_projection_dot


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
VERIFICATION_PATH = ROOT / "verification-69e.json"
OUTPUT_PATH = ROOT / "dependency-graph-69e.json"
DOT_PATH = ROOT / "dependency-graph-69e.dot"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    verification = json.loads(VERIFICATION_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    if not verification["valid"]:
        raise ValueError("依赖图只能从验证通过的证书生成")
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
    }
    return analyze_dependency_graph(certificate, verification, source)


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    DOT_PATH.write_text(
        render_paid_projection_dot(report),
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote={OUTPUT_PATH}")
    print(f"wrote={DOT_PATH}")
    print(
        "nodes="
        f"{report['summary']['program_nodes']} "
        f"paid={report['summary']['paid_nodes']} "
        f"edges={report['summary']['edges']}"
    )
    print(
        "syntactically_dead_paid_nodes="
        f"{report['summary']['syntactically_dead_paid_nodes']}"
    )


if __name__ == "__main__":
    main()
