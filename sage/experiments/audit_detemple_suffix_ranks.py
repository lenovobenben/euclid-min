"""审计已知 19 E 后缀在当前启发式候选排序中的可见性。"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform

from sage.version import version as sage_version

from euclid_min.formats import load_profile
from euclid_min.search import Candidate, Regular17CandidateHeuristic
from euclid_min.search.candidates import generate_prefiltered_candidates
from euclid_min.search.export import steps_from_program
from euclid_min.search.model import SearchNode
from experiments.build_detemple_1991_improved import (
    DEFAULT_PROFILE,
    build_program,
)
from experiments.search_detemple_suffix import SAGE_IMAGE, exact_prefix


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e12-known-19e-suffix-rank-audit-sage-10.7.json"
)
LEVEL_LIMITS = (5, 6, 7, 8)
WIDTHS = (8, 12, 32)


def _canonical_point(node: SearchNode, target):
    for point in node.state.points:
        if point == target:
            return point
    raise ValueError("已知后缀步骤引用了当前状态中不存在的点")


def _candidate_key(heuristic, candidate: Candidate):
    return heuristic.operation_key(
        candidate.op,
        candidate.first,
        candidate.second,
    )


def _selected_keys(heuristic, candidates) -> set[tuple]:
    return {
        _candidate_key(heuristic, candidate)
        for candidate in candidates
    }


def audit(profile_path: Path) -> dict:
    program = build_program()
    all_steps = steps_from_program(program)
    initial_node, _prefix = exact_prefix("c_M1_2_Ay")
    suffix_steps = all_steps[initial_node.score :]
    draw_entries = [
        entry for entry in program if entry["op"] in ("line", "circle")
    ]
    suffix_entries = draw_entries[initial_node.score :]
    if len(suffix_steps) != 7 or len(suffix_entries) != 7:
        raise RuntimeError("已知 19 E 构造的 E12 后缀不再是 7 个收费操作")

    profile = load_profile(profile_path)
    node = initial_node
    records = []
    for entry, step in zip(suffix_entries, suffix_steps):
        first = _canonical_point(node, step.first)
        second = _canonical_point(node, step.second)
        known = Candidate(step.op, first, second)
        raw_operation_count = (
            3 * len(node.state.points) * (len(node.state.points) - 1) // 2
        )
        level_results = {}
        for level_limit in LEVEL_LIMITS:
            heuristic = Regular17CandidateHeuristic(
                max_input_level=level_limit
            )
            heuristic.prepare_state(node.state, include_complexity=True)
            known_key = _candidate_key(heuristic, known)
            full_candidates, raw_count, eligible_count = (
                generate_prefiltered_candidates(
                    node.state,
                    limit=max(1, raw_operation_count),
                    score_operation=heuristic.evaluate_points,
                    operation_key=heuristic.operation_key,
                    operation_level=heuristic.operation_level,
                    exact_deduplicate=False,
                    diversify=False,
                )
            )
            if raw_count != raw_operation_count:
                raise RuntimeError("原始候选计数与点数公式不一致")
            target_keys = [
                _candidate_key(heuristic, candidate)
                for candidate in full_candidates
            ]
            target_rank = (
                target_keys.index(known_key) + 1
                if known_key in target_keys
                else None
            )
            diverse_retained = {}
            for width in WIDTHS:
                diverse_candidates, _raw, _eligible = (
                    generate_prefiltered_candidates(
                        node.state,
                        limit=width,
                        score_operation=heuristic.evaluate_points,
                        operation_key=heuristic.operation_key,
                        operation_level=heuristic.operation_level,
                        exact_deduplicate=False,
                        diversify=True,
                    )
                )
                diverse_retained[str(width)] = (
                    known_key
                    in _selected_keys(heuristic, diverse_candidates)
                )
            score = heuristic.evaluate(node.state, known)
            complexity = heuristic.candidate_complexity(known)
            level_results[str(level_limit)] = {
                "eligible_operations": eligible_count,
                "unique_operations": len(full_candidates),
                "target_rank": target_rank,
                "target_retained": {
                    str(width): (
                        target_rank is not None and target_rank <= width
                    )
                    for width in WIDTHS
                },
                "diverse_retained": diverse_retained,
                "candidate_score": asdict(score) if score is not None else None,
                "candidate_complexity": asdict(complexity),
            }

        records.append(
            {
                "e_move": node.score + 1,
                "program_id": entry["id"],
                "op": known.op,
                "points_before": len(node.state.points),
                "raw_operations": raw_operation_count,
                "input_level": max(
                    node.state.point_level(first),
                    node.state.point_level(second),
                ),
                "levels": level_results,
            }
        )
        node = node.apply(known)

    return {
        "schema": "euclid-min-known-suffix-rank-audit/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "heuristic_diagnostic_nonproof",
        "environment": {
            "sage_version": sage_version,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "docker_image": SAGE_IMAGE,
        },
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "prefix_last_id": "c_M1_2_Ay",
        "prefix_e_move": initial_node.score,
        "known_total_e_move": node.score,
        "level_limits": list(LEVEL_LIMITS),
        "widths": list(WIDTHS),
        "steps": records,
        "interpretation_boundary": (
            "该审计只衡量已知 19 E 路径在当前预筛中的可见性；"
            "它既不证明搜索完备，也不提供 18 E 下界。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
