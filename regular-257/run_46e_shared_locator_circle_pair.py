"""仅用于复现旧强制降域路径的单任务对调试器。

该路径在第 8 对上使用 6 GiB PARI 栈运行约 3 小时 7 分钟仍未返回，
不是正式搜索入口。只有显式确认时才允许执行。
"""

from __future__ import annotations

import argparse
import json

from sage.all import pari

from build_46e_shared_locator_circle_search import ROOT, build_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pair_index", type=int, choices=range(1, 16))
    parser.add_argument(
        "--allow-expensive-field-exactification",
        action="store_true",
        help="明确允许复现已知高成本、不可检查点的强制降域路径",
    )
    parser.add_argument(
        "--pari-stack-gib",
        type=int,
        choices=range(1, 7),
        default=6,
        help="PARI 栈上限（GiB）；不得超过当前 7.66 GiB 容器总内存",
    )
    args = parser.parse_args()
    if not args.allow_expensive_field_exactification:
        parser.error(
            "该入口只复现已知低价值强制降域；"
            "若确实需要，请显式加上 "
            "--allow-expensive-field-exactification"
        )
    # 某些 46E 抽象圆心来自两个高次圆分支；2 GiB PARI 栈已经
    # 实测溢出。单进程复核提高到 6 GiB，仍为 Sage/Python 保留约
    # 1.6 GiB 容器内存；不要将该上限套用到并行 worker。
    pari.allocatemem(args.pari_stack_gib * 1024**3)
    report = build_report(
        trace=True,
        workers=1,
        pair_indices={args.pair_index},
    )
    output = ROOT / "tmp" / f"shared-locator-circle-pair-{args.pair_index}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
