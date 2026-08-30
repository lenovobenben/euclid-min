"""从 DeTemple 19 E 构造的精确中间状态搜索更短联合后缀。

该实验默认保留前 12 E，允许最多再画 6 个对象。beam search 和浮点评分
只负责候选保留；任何命中都会重建为完整证书并交给独立 verifier 检查。
未命中始终只表示启发式保留范围内没有候选，不构成下界。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from dataclasses import asdict
from pathlib import Path

from sage.version import version as sage_version

from euclid_min.search import (
    ParallelHeuristicBeamSearch,
    Regular17CandidateHeuristic,
    Regular17Goal,
    Regular17Heuristic,
    Regular17OneMoveHeuristic,
)
from euclid_min.search.export import (
    build_certificate_from_steps,
    node_from_steps,
    steps_from_program,
)
from euclid_min.formats import load_profile
from euclid_min.verifier import verify_files
from experiments.build_detemple_1991_improved import (
    DEFAULT_PROFILE,
    build_program,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "candidates" / "regular-17-18e.json"
SAGE_IMAGE = (
    "sagemath/sagemath@sha256:"
    "4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528"
)


def exact_prefix(last_entry_id: str):
    """返回截至指定程序条目的完整闭包搜索节点及原始前缀。"""

    program = build_program()
    try:
        last_index = next(
            index for index, entry in enumerate(program)
            if entry["id"] == last_entry_id
        )
    except StopIteration as error:
        raise ValueError(f"未知前缀条目 ID：{last_entry_id}") from error
    prefix = program[: last_index + 1]
    node = node_from_steps(steps_from_program(prefix))
    return node, prefix


def run_search(
    *,
    prefix_last_id: str,
    max_total_score: int,
    beam_width: int,
    candidate_width: int | None,
    workers: int,
    state_timeout_seconds: float | None,
    max_input_level: int | None,
    candidate_strategy: str,
    max_states: int | None,
    heuristic_name: str,
    profile_path: Path,
):
    initial_node, prefix = exact_prefix(prefix_last_id)
    if max_total_score < initial_node.score:
        raise ValueError("总分上限不能小于前缀分数")
    if candidate_width is None or state_timeout_seconds is None:
        raise ValueError("并行后缀搜索要求候选宽度和状态超时")
    heuristic = (
        Regular17OneMoveHeuristic()
        if heuristic_name == "one-move"
        else Regular17Heuristic()
    )
    profile = load_profile(profile_path)
    outcome = ParallelHeuristicBeamSearch().search(
        Regular17Goal(),
        heuristic,
        Regular17CandidateHeuristic(
            max_input_level=max_input_level,
        ),
        max_score=max_total_score,
        beam_width=beam_width,
        max_states=max_states,
        initial_node=initial_node,
        candidate_width=candidate_width,
        progress=lambda event: print(
            json.dumps({"progress": event}, ensure_ascii=False),
            file=sys.stderr,
            flush=True,
        ),
        workers=workers,
        state_timeout_seconds=state_timeout_seconds,
        diversify_candidates=candidate_strategy == "diverse",
    )
    summary = {
        "schema": "euclid-min-suffix-search-summary/v1",
        "mode": "heuristic_nonproof",
        "environment": {
            "sage_version": sage_version,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "docker_image": SAGE_IMAGE,
        },
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "prefix_last_id": prefix_last_id,
        "prefix_program_entries": len(prefix),
        "prefix_e_move": initial_node.score,
        "max_total_score": max_total_score,
        "suffix_budget": max_total_score - initial_node.score,
        "beam_width": beam_width,
        "candidate_width": candidate_width,
        "workers": workers,
        "state_timeout_seconds": state_timeout_seconds,
        "max_input_level": max_input_level,
        "candidate_strategy": candidate_strategy,
        "max_states": max_states,
        "heuristic": heuristic_name,
        "status": outcome.status,
        "found_score": outcome.node.score if outcome.node else None,
        "stats": asdict(outcome.stats),
        "interpretation_boundary": (
            "浮点启发式会删除分支；未命中不构成 18 E 不存在的证明。"
        ),
    }
    return outcome, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix-last-id", default="c_M1_2_Ay")
    parser.add_argument("--max-total-score", type=int, default=18)
    parser.add_argument("--beam-width", type=int, default=4)
    parser.add_argument(
        "--candidate-width",
        type=int,
        default=8,
        help="每个父状态经浮点预排序后进行精确展开的候选上限",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="用于独立精确候选扩展的进程数",
    )
    parser.add_argument(
        "--state-timeout-seconds",
        type=float,
        default=8.0,
        help="单个父状态全部候选的并行精确扩展时间上限",
    )
    parser.add_argument(
        "--max-input-level",
        type=int,
        default=8,
        help="候选两个输入点允许的最高生成依赖层级",
    )
    parser.add_argument(
        "--candidate-strategy",
        choices=("diverse", "target-only"),
        default="diverse",
    )
    parser.add_argument("--max-states", type=int)
    parser.add_argument(
        "--heuristic",
        choices=("one-move", "regular"),
        default="one-move",
    )
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="无论是否命中，都把最终非证明实验摘要写入 JSON",
    )
    parser.add_argument(
        "--write-candidate",
        action="store_true",
        help="仅在找到并独立验证候选后写入 --output",
    )
    args = parser.parse_args()

    outcome, summary = run_search(
        prefix_last_id=args.prefix_last_id,
        max_total_score=args.max_total_score,
        beam_width=args.beam_width,
        candidate_width=args.candidate_width,
        workers=args.workers,
        state_timeout_seconds=args.state_timeout_seconds,
        max_input_level=args.max_input_level,
        candidate_strategy=args.candidate_strategy,
        max_states=args.max_states,
        heuristic_name=args.heuristic,
        profile_path=args.profile,
    )
    if outcome.node is not None:
        certificate = build_certificate_from_steps(
            outcome.node.steps,
            profile_path=args.profile,
            construction_id="regular-17-suffix-search-candidate",
            title="Regular 17-gon candidate from exact-prefix suffix search",
        )
        if args.write_candidate:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(certificate, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            report = verify_files(args.output, args.profile)
            summary["candidate_path"] = str(args.output)
            summary["independent_verifier_valid"] = report.valid
            if not report.valid:
                if args.summary_output is not None:
                    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
                    args.summary_output.write_text(
                        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                print(json.dumps(summary, ensure_ascii=False, indent=2))
                return 2

    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if outcome.node is not None else 4


if __name__ == "__main__":
    raise SystemExit(main())
