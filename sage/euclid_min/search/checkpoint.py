"""严格、可恢复的搜索 frontier checkpoint。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..errors import VerificationError
from ..formats import (
    _load_schema,
    _unique_json_object,
    _validate_schema_instance,
    load_profile,
)
from .export import build_program_from_steps, node_from_steps, steps_from_program
from .model import SearchNode, SearchStats


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHECKPOINT_SCHEMA = (
    REPOSITORY_ROOT / "schemas" / "search-checkpoint-v1.schema.json"
)


@dataclass(frozen=True, slots=True)
class LoadedCheckpoint:
    max_score: int
    frontier: tuple[SearchNode, ...]
    previous_stats: SearchStats


def save_checkpoint(
    path: str | Path,
    *,
    profile_path: str | Path,
    max_score: int,
    frontier: tuple[SearchNode, ...],
    stats: SearchStats,
) -> None:
    if not frontier:
        raise ValueError("不能保存空 frontier checkpoint")
    profile = load_profile(profile_path)
    payload = {
        "schema": "euclid-min-search-checkpoint/v1",
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "strategy": "bounded_breadth_first",
        "max_score": max_score,
        "frontier": [
            {
                "score": node.score,
                "program": build_program_from_steps(node.steps)[0],
            }
            for node in frontier
        ],
        "previous_stats": asdict(stats),
    }
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_checkpoint(
    path: str | Path,
    *,
    profile_path: str | Path,
    schema_path: str | Path = DEFAULT_CHECKPOINT_SCHEMA,
) -> LoadedCheckpoint:
    checkpoint_path = Path(path)
    try:
        text = checkpoint_path.read_text(encoding="utf-8")
        data = json.loads(text, object_pairs_hook=_unique_json_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(
            "checkpoint_json_invalid",
            f"无法读取 checkpoint: {error}",
        ) from error
    _validate_schema_instance(
        data,
        _load_schema(schema_path),
        "checkpoint_schema_invalid",
    )
    profile = load_profile(profile_path)
    if data["profile"] != {
        "id": profile.data["id"],
        "sha256": profile.sha256,
    }:
        raise VerificationError(
            "checkpoint_profile_mismatch",
            "checkpoint 与加载的 profile 不一致",
        )

    frontier: list[SearchNode] = []
    for item in data["frontier"]:
        steps = steps_from_program(item["program"])
        if len(steps) != item["score"]:
            raise VerificationError(
                "checkpoint_score_mismatch",
                "checkpoint 节点 score 与程序绘制数不一致",
            )
        frontier.append(node_from_steps(steps))
    return LoadedCheckpoint(
        max_score=data["max_score"],
        frontier=tuple(frontier),
        previous_stats=SearchStats(**data["previous_stats"]),
    )
