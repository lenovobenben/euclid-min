"""生成 46E 状态中跨根载线共享定位点的新圆搜索报告。

当前为实验性核心：前 7 个任务对已完成，第 8 对暴露出抽象圆心过早
降域的高成本路径。全量 CLI 在抽象消元和任务对检查点完成前主动禁用。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from shared_locator_circle_search import search_shared_locator_circles


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
GA_IR_PATH = ROOT / "geometry-algebra-baseline-69e.json"
CHORD_IR_PATH = ROOT / "tail-quadratic-chord-ir-68e.json"
LINE_SEARCH_PATH = ROOT / "shared-locator-line-search-46e.json"
OUTPUT_PATH = ROOT / "shared-locator-circle-search-46e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(
    *,
    trace: bool = False,
    workers: int | None = None,
    pair_indices: set[int] | None = None,
) -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    full_closure = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    ga_ir = json.loads(GA_IR_PATH.read_text(encoding="utf-8"))
    chord_ir = json.loads(CHORD_IR_PATH.read_text(encoding="utf-8"))
    line_search = json.loads(LINE_SEARCH_PATH.read_text(encoding="utf-8"))
    certificate_sha256 = _sha256_file(CERTIFICATE_PATH)
    ga_ir_sha256 = _sha256_file(GA_IR_PATH)
    chord_ir_sha256 = _sha256_file(CHORD_IR_PATH)
    if full_closure["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("完整闭包对应的证书 SHA-256 不一致")
    if ga_ir["source"]["certificate_sha256"] != certificate_sha256:
        raise ValueError("GA-IR 对应的证书 SHA-256 不一致")
    if chord_ir["source"]["geometry_algebra_ir_sha256"] != ga_ir_sha256:
        raise ValueError("根载线 IR 对应的 GA-IR SHA-256 不一致")
    if line_search["source"]["tail_quadratic_chord_ir_sha256"] != chord_ir_sha256:
        raise ValueError("共享定位点直线搜索对应的根载线 IR SHA-256 不一致")
    source = {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": certificate_sha256,
        "construction_sha256": certificate["integrity"]["construction_sha256"],
        "full_intersection_closure": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_sha256": _sha256_file(FULL_CLOSURE_PATH),
        "geometry_algebra_ir": GA_IR_PATH.name,
        "geometry_algebra_ir_sha256": ga_ir_sha256,
        "tail_quadratic_chord_ir": CHORD_IR_PATH.name,
        "tail_quadratic_chord_ir_sha256": chord_ir_sha256,
        "shared_locator_line_search": LINE_SEARCH_PATH.name,
        "shared_locator_line_search_sha256": _sha256_file(LINE_SEARCH_PATH),
    }
    tracer = (lambda message: print(message, flush=True)) if trace else None
    return search_shared_locator_circles(
        certificate,
        ga_ir,
        chord_ir,
        source,
        workers=workers,
        pair_indices=pair_indices,
        trace=tracer,
    )


def main() -> None:
    raise SystemExit(
        "全量共享定位圆搜索尚未完成：请先实现抽象圆心消元与任务对检查点；"
        "不要再运行 QQbar -> CyclotomicField(257) 强制降域路径。"
    )


if __name__ == "__main__":
    main()
