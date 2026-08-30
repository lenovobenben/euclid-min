"""Euclid-Min 的 Sage Python 命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from .errors import VerificationError
from .formats import load_profile
from .search import (
    BoundedBreadthFirstSearch,
    DeterministicBeamSearch,
    Regular17Goal,
    Regular17Heuristic,
)
from .search.checkpoint import load_checkpoint, save_checkpoint
from .search.export import build_certificate_from_steps
from .verifier import VerificationReport, verify_files
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="euclid-min",
        description="正十七边形构造的 SageMath 精确验证与基础搜索工具",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify", help="验证构造证书")
    verify_parser.add_argument("certificate", help="证书 JSON 文件")
    verify_parser.add_argument(
        "--profile",
        required=True,
        help="profile YAML 文件",
    )
    verify_parser.add_argument(
        "--json",
        action="store_true",
        help="把完整验证报告以 JSON 输出到 stdout",
    )
    verify_parser.add_argument(
        "--report",
        help="另存完整 JSON 验证报告",
    )

    search_parser = subparsers.add_parser("search", help="运行小深度精确搜索")
    search_parser.add_argument("--profile", required=True, help="profile YAML 文件")
    search_parser.add_argument(
        "--max-score",
        required=True,
        type=int,
        help="本次搜索允许的最大 E-score",
    )
    search_parser.add_argument(
        "--max-states",
        type=int,
        default=1000,
        help="在完整展开当前节点后暂停的状态软上限（默认 1000）",
    )
    search_parser.add_argument(
        "--strategy",
        choices=("bfs", "beam"),
        default="bfs",
        help="bfs 为小深度完备模式；beam 为非证明启发式模式",
    )
    search_parser.add_argument(
        "--beam-width",
        type=int,
        default=32,
        help="beam 模式每层保留的状态数（默认 32）",
    )
    search_parser.add_argument("--checkpoint", help="达到状态上限时保存 frontier")
    search_parser.add_argument("--resume", help="从已有 checkpoint 恢复 frontier")
    search_parser.add_argument("--output", help="命中后写入已独立验证的证书 JSON")
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 输出搜索摘要",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "search":
        return _run_search(args)
    if args.command != "verify":
        return 2

    report = verify_files(args.certificate, args.profile)
    if args.report:
        try:
            _write_report(Path(args.report), report)
        except OSError as error:
            print(f"无法写入验证报告：{error}", file=sys.stderr)
            return 2

    if args.json:
        print(_report_json(report))
    else:
        _print_human_report(report)
    return 0 if report.valid else 1


def _run_search(args: argparse.Namespace) -> int:
    try:
        profile = load_profile(args.profile)
        initial_frontier = None
        resumed_from = None
        if args.strategy == "beam" and (args.resume or args.checkpoint):
            raise ValueError("beam 模式暂不支持 frontier checkpoint")
        if args.resume:
            checkpoint = load_checkpoint(
                args.resume,
                profile_path=args.profile,
            )
            if args.max_score < checkpoint.max_score:
                raise ValueError(
                    "恢复搜索的 max-score 不能小于 checkpoint 的 max_score"
                )
            initial_frontier = checkpoint.frontier
            resumed_from = str(args.resume)

        if args.strategy == "bfs":
            outcome = BoundedBreadthFirstSearch().search(
                Regular17Goal(),
                max_score=args.max_score,
                max_states=args.max_states,
                initial_frontier=initial_frontier,
            )
            strategy_name = "bounded_breadth_first"
        else:
            outcome = DeterministicBeamSearch().search(
                Regular17Goal(),
                Regular17Heuristic(),
                max_score=args.max_score,
                beam_width=args.beam_width,
                max_states=args.max_states,
            )
            strategy_name = "deterministic_target_beam"
        certificate_path = None
        if outcome.status == "found":
            certificate = build_certificate_from_steps(
                outcome.node.steps,
                profile_path=args.profile,
            )
            serialized = json.dumps(certificate, ensure_ascii=False, indent=2) + "\n"
            with tempfile.TemporaryDirectory() as temporary_directory:
                temporary_path = Path(temporary_directory) / "candidate.json"
                temporary_path.write_text(serialized, encoding="utf-8")
                independent_report = verify_files(temporary_path, args.profile)
            if not independent_report.valid:
                raise RuntimeError(
                    "搜索候选未通过独立 verifier："
                    f"{independent_report.data['error']['code']}"
                )
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(serialized, encoding="utf-8")
                certificate_path = str(output_path)
        elif outcome.status == "state_limit" and args.checkpoint:
            save_checkpoint(
                args.checkpoint,
                profile_path=args.profile,
                max_score=args.max_score,
                frontier=outcome.frontier,
                stats=outcome.stats,
            )

        summary = {
            "profile": {"id": profile.data["id"], "sha256": profile.sha256},
            "strategy": strategy_name,
            "search_mode": "complete_bounded"
            if args.strategy == "bfs"
            else "heuristic_nonproof",
            "max_score": args.max_score,
            "max_states": args.max_states,
            "beam_width": args.beam_width if args.strategy == "beam" else None,
            "status": outcome.status,
            "score": outcome.node.score if outcome.node is not None else None,
            "stats": asdict(outcome.stats),
            "checkpoint": str(args.checkpoint)
            if outcome.status == "state_limit" and args.checkpoint
            else None,
            "resumed_from": resumed_from,
            "certificate": certificate_path,
        }
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            _print_search_summary(summary)
        return {
            "found": 0,
            "exhausted": 1,
            "state_limit": 3,
            "heuristic_limit": 4,
        }[outcome.status]
    except (VerificationError, ValueError, RuntimeError, OSError) as error:
        print(f"搜索失败：{error}", file=sys.stderr)
        return 2


def _write_report(path: Path, report: VerificationReport) -> None:
    path.write_text(_report_json(report) + "\n", encoding="utf-8")


def _report_json(report: VerificationReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)


def _print_human_report(report: VerificationReport) -> None:
    data = report.data
    print(f"构造有效：{'是' if report.valid else '否'}")
    if not report.valid:
        error = data["error"]
        print(f"错误：[{error['code']}] {error['message']}")
        if "program_index" in error:
            print(f"程序索引：{error['program_index']}")
        if "entry_id" in error:
            print(f"条目 ID：{error['entry_id']}")
        return

    print(f"Profile：{data['profile']['id']}")
    print(f"E-score：{data['score']['e_move']}")
    print(f"目标：{', '.join(data['targets'])}")
    print(f"首次命中程序索引：{data['first_target_program_index']}")
    print(f"支持的声明等级：{data['supported_claim']}")


def _print_search_summary(summary: dict) -> None:
    status_labels = {
        "found": "已找到并通过独立验证",
        "exhausted": "在给定深度内穷尽，未命中",
        "state_limit": "达到状态软上限，已暂停",
        "heuristic_limit": "启发式保留范围已用尽，未命中",
    }
    print(f"搜索状态：{status_labels[summary['status']]}")
    print(f"Profile：{summary['profile']['id']}")
    print(f"最大 E-score：{summary['max_score']}")
    print(f"已展开状态：{summary['stats']['expanded_states']}")
    print(f"已生成候选：{summary['stats']['generated_candidates']}")
    print(f"搜索耗时：{summary['stats']['elapsed_seconds']:.6f} 秒")
    if summary["score"] is not None:
        print(f"命中 E-score：{summary['score']}")
    if summary["checkpoint"] is not None:
        print(f"Checkpoint：{summary['checkpoint']}")
    if summary["certificate"] is not None:
        print(f"证书：{summary['certificate']}")
