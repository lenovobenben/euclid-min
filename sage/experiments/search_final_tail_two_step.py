"""从已知 E16 状态搜索至多两步直接命中任一正十七边形目标。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from euclid_min.search import Candidate, PointGoal
from euclid_min.search.export import (
    build_certificate_from_steps,
    node_from_steps,
    steps_from_program,
)
from euclid_min.target import adjacent_targets
from euclid_min.verifier import verify_files
from experiments.build_detemple_1991_improved import (
    DEFAULT_PROFILE,
    build_program,
)
from experiments.search_m04_three_step import (
    _canonical_candidate,
    _numeric_first_step_scores,
    _search_exact_batches,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "candidates" / "regular-17-18e-tail.json"
DEFAULT_SUMMARY_OUTPUT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e16-final-tail-two-step-search-sage-10.7.json"
)


def run(args):
    started_at = perf_counter()
    known_steps = steps_from_program(build_program())
    initial = node_from_steps(known_steps[:16])
    results = []
    hit_record = None
    for target_name, target in adjacent_targets().items():
        ranked = _numeric_first_step_scores(initial, target, args.workers)
        print(
            json.dumps(
                {
                    "event": "numeric_ranking_end",
                    "target": target_name.value,
                    "candidates": len(ranked),
                    "best": [
                        {
                            "index": row.index,
                            "first_residual": row.first_residual,
                            "second_residual": row.second_residual,
                            "new_numeric_points": row.new_numeric_points,
                        }
                        for row in ranked[:5]
                    ],
                }
            ),
            flush=True,
        )
        hit, completed, timed_out, target_candidates_tested = (
            _search_exact_batches(
                initial,
                target,
                ranked,
                limit=args.first_step_limit,
                workers=args.workers,
                batch_size=args.batch_size,
                batch_timeout_seconds=args.batch_timeout_seconds,
                max_local_steps=2,
            )
        )
        result = {
            "target": target_name.value,
            "first_step_candidates": len(ranked),
            "exact_first_steps_completed": completed,
            "exact_first_steps_timed_out": timed_out,
            "exact_target_candidates_tested": target_candidates_tested,
            "found_local_steps": len(hit[1]) if hit is not None else None,
        }
        results.append(result)
        if hit is not None:
            hit_record = (target_name, target, hit)
            break

    certificate_valid = None
    found_score = None
    if hit_record is not None:
        _target_name, target, (_index, local_steps) = hit_record
        node = initial
        for candidate in local_steps:
            node = node.apply(_canonical_candidate(node, candidate))
        if not PointGoal(target).reached(node.state):
            raise RuntimeError("两步尾部搜索返回的路径没有精确命中目标")
        certificate = build_certificate_from_steps(
            node.steps,
            profile_path=args.profile,
            construction_id="regular-17-final-tail-two-step-candidate",
            title="Regular 17-gon candidate from two-step final-tail search",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(certificate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report = verify_files(args.output, args.profile)
        certificate_valid = report.valid
        found_score = node.score

    summary = {
        "schema": "euclid-min-final-tail-two-step-search/v1",
        "mode": "heuristic_nonproof",
        "prefix_e_move": initial.score,
        "local_budget": 2,
        "first_step_limit": args.first_step_limit,
        "workers": args.workers,
        "batch_size": args.batch_size,
        "batch_timeout_seconds": args.batch_timeout_seconds,
        "targets": results,
        "found_total_e_move": found_score,
        "certificate_valid": certificate_valid,
        "elapsed_seconds": perf_counter() - started_at,
        "interpretation_boundary": (
            "两个镜像目标分别使用浮点第一步排序和固定 top-N；未命中不是下界。"
        ),
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if certificate_valid else 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT
    )
    parser.add_argument("--first-step-limit", type=int, default=128)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--batch-timeout-seconds", type=float, default=30.0)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
