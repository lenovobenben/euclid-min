"""生成 M5 搜索 profiling 的可复现 JSON 摘要。"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from sage.version import version as sage_version
from jsonschema import Draft202012Validator

from euclid_min.formats import load_profile
from euclid_min.search import (
    BoundedBreadthFirstSearch,
    DeterministicBeamSearch,
    Regular17Goal,
    Regular17Heuristic,
)
from euclid_min.target import adjacent_targets


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT / "benchmarks" / "m5-search-profile-sage-10.7.json"
)
PROFILE_SCHEMA = REPOSITORY_ROOT / "schemas" / "search-profile-v1.schema.json"
SAGE_IMAGE = (
    "sagemath/sagemath@sha256:"
    "4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528"
)


def run_profiles() -> list[dict]:
    goal = Regular17Goal()
    heuristic = Regular17Heuristic()
    cases = []

    bfs_depth_two = BoundedBreadthFirstSearch().search(
        goal,
        max_score=2,
        max_states=1000,
    )
    cases.append(
        _case(
            "bfs-depth-2-complete",
            "bounded_breadth_first",
            {"max_score": 2, "max_states": 1000},
            bfs_depth_two,
        )
    )

    bfs_limited = BoundedBreadthFirstSearch().search(
        goal,
        max_score=3,
        max_states=100,
    )
    cases.append(
        _case(
            "bfs-depth-3-state-limit",
            "bounded_breadth_first",
            {"max_score": 3, "max_states": 100},
            bfs_limited,
        )
    )

    beam_depth_three = DeterministicBeamSearch().search(
        goal,
        heuristic,
        max_score=3,
        beam_width=8,
        max_states=2000,
    )
    cases.append(
        _case(
            "beam-depth-3-width-8",
            "deterministic_target_beam",
            {"max_score": 3, "max_states": 2000, "beam_width": 8},
            beam_depth_three,
        )
    )
    return cases


def _case(name: str, strategy: str, parameters: dict, outcome) -> dict:
    return {
        "name": name,
        "strategy": strategy,
        "parameters": parameters,
        "status": outcome.status,
        "score": outcome.node.score if outcome.node is not None else None,
        "stats": asdict(outcome.stats),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    profile = load_profile(args.profile)
    # 首次构造 17 次单位根相关 AA 常数属于固定初始化成本，不混入搜索扩展计时。
    adjacent_targets()
    payload = {
        "schema": "euclid-min-search-profile/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "sage_version": sage_version,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "docker_image": SAGE_IMAGE,
            "target_cache_warmed": True,
        },
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "cases": run_profiles(),
        "interpretation_boundary": (
            "Timings are diagnostic and machine-dependent. Heuristic pruning "
            "does not support lower-bound or optimality claims."
        ),
    }
    schema = json.loads(PROFILE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
