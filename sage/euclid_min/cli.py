"""Euclid-Min 的 Sage Python 命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .verifier import VerificationReport, verify_files
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="euclid-min",
        description="正十七边形构造的 SageMath 精确验证器",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
