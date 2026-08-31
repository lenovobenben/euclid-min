"""重建 M7 深度 3 frontier，并完整扫描每个状态的两步目标义务。"""

from __future__ import annotations

import argparse
import json
import multiprocessing
from pathlib import Path
from time import perf_counter

from euclid_min.formats import load_profile
from euclid_min.search import SearchNode
from euclid_min.search.backward import expand_regular17_two_step_obligations
from euclid_min.search.candidates import generate_candidates
from euclid_min.search.index import HorizontalReflectionStateIndex


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "m7-two-step-obligation-scan-sage-10.7.json"
)
_FRONTIER = ()


def _build_frontier(max_score: int = 3):
    index = HorizontalReflectionStateIndex()
    initial = SearchNode.initial()
    if not index.add_if_better(initial.state, initial.score):
        raise RuntimeError("初始状态不应被状态索引拒绝")
    frontier = (initial,)
    layers = []
    for score in range(max_score):
        children = []
        generated = 0
        equivalent_pruned = 0
        for node in frontier:
            for candidate in generate_candidates(node.state):
                generated += 1
                child = node.apply(candidate)
                if not index.add_if_better(child.state, child.score):
                    equivalent_pruned += 1
                    continue
                children.append(child)
        layers.append(
            {
                "score": score,
                "frontier_states": len(frontier),
                "generated_candidates": generated,
                "accepted_next_states": len(children),
                "equivalent_pruned": equivalent_pruned,
            }
        )
        frontier = tuple(children)
    return frontier, layers


def _scan_frontier_state(index: int):
    expansion = expand_regular17_two_step_obligations(_FRONTIER[index].state)
    return {
        "precursor_candidates": expansion.precursor_candidates,
        "terminal_parameterizations_tested": (
            expansion.terminal_parameterizations_tested
        ),
        "one_step_target_branches": sum(
            bool(branch.targets) for branch in expansion.branches
        ),
        "terminal_candidates": expansion.terminal_candidates,
        "successful_branches": len(expansion.successful_branches),
    }


def run(*, profile_path: Path, output_path: Path, workers: int) -> dict:
    if workers < 1:
        raise ValueError("workers 至少为 1")
    profile = load_profile(profile_path)
    started_at = perf_counter()
    frontier, forward_layers = _build_frontier()
    global _FRONTIER
    _FRONTIER = frontier

    if workers == 1:
        rows = [_scan_frontier_state(index) for index in range(len(frontier))]
    else:
        context = multiprocessing.get_context("fork")
        with context.Pool(processes=workers) as pool:
            rows = pool.map(
                _scan_frontier_state,
                range(len(frontier)),
                chunksize=1,
            )

    totals = {
        key: sum(row[key] for row in rows)
        for key in (
            "precursor_candidates",
            "terminal_parameterizations_tested",
            "one_step_target_branches",
            "terminal_candidates",
            "successful_branches",
        )
    }
    payload = {
        "schema": "euclid-min-two-step-obligation-scan/v1",
        "mode": "proof_candidate_unchecked",
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "target": {
            "type": "regular_polygon_adjacent_vertex",
            "polygon_sides": 17,
            "accepted": ["B_plus", "B_minus"],
        },
        "forward": {
            "max_score": 3,
            "frontier_states": len(frontier),
            "layers": forward_layers,
            "safe_reductions": [
                "duplicate_draw_dominance",
                "same_object_parameterization_equivalence",
                "exact_state_equivalence",
                "horizontal_reflection_equivalence",
            ],
        },
        "suffix": {
            "budget": 2,
            "strategy": "complete_state_relative_and_or_expansion",
            **totals,
        },
        "result": {
            "status": (
                "no_target_in_generator_scan"
                if totals["successful_branches"] == 0
                else "target_found"
            ),
            "covered_total_score": 5,
        },
        "execution": {
            "workers": workers,
            "elapsed_seconds": perf_counter() - started_at,
            "container_image": (
                "sagemath/sagemath@sha256:"
                "4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528"
            ),
        },
        "interpretation_boundary": (
            "生成器已完整扫描其声明的有限空间，但该记录尚未由独立参考 checker "
            "重放；它本身不能升级下界，正式结论应引用 bounded-proof/v2。"
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    payload = run(
        profile_path=args.profile,
        output_path=args.output,
        workers=args.workers,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
