"""小深度有界穷尽的确定性证明记录与参考重放检查器。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from ..errors import VerificationError
from ..formats import (
    _load_schema,
    _unique_json_object,
    _validate_schema_instance,
    load_profile,
)
from ..geometry import Circle, Drawable, Line
from ..state import GeometryState
from .candidates import generate_candidates
from .backward import is_regular17_terminal_step
from .index import (
    ExactStateIndex,
    HorizontalReflectionStateIndex,
    states_equal,
)
from .model import Candidate, Regular17Goal, SearchGoal, SearchNode
from .symmetry import states_equal_under_horizontal_reflection


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROOF_SCHEMA = REPOSITORY_ROOT / "schemas" / "bounded-proof-v1.schema.json"
SUPPORTED_PROFILE_ID = "regular-17-e-fixed-v1"
SUPPORTED_PROFILE_SHA256 = (
    "bb0a4ea904e60fb688da15558fa8f09982d4a7eee3cd8efee32ae9cb61079014"
)


@dataclass(frozen=True, slots=True)
class ProofLayer:
    """一个 E-score 层的完整枚举计数。"""

    score: int
    frontier_states: int
    goal_states: int
    expanded_states: int
    generated_candidates: int
    accepted_next_states: int
    equivalent_pruned: int
    terminal_candidates: int
    terminal_nonmatching_pruned: int


@dataclass(frozen=True, slots=True)
class ProofEnumeration:
    """不含墙钟时间的确定性有界枚举结果。"""

    status: str
    minimum_score: int | None
    layers: tuple[ProofLayer, ...]
    expanded_states: int
    generated_candidates: int
    accepted_states: int
    equivalent_pruned: int
    terminal_candidates: int
    terminal_nonmatching_pruned: int
    max_frontier: int
    goal_tests: int
    node: SearchNode | None = None


class _LinearExactStateIndex:
    """参考检查器使用的无摘要线性精确状态索引。"""

    def __init__(self, *, horizontal_reflection: bool = False) -> None:
        self._entries: list[tuple[GeometryState, int]] = []
        self._horizontal_reflection = horizontal_reflection

    def add_if_better(self, state: GeometryState, score: int) -> bool:
        for index, (existing, existing_score) in enumerate(self._entries):
            equivalent = states_equal(existing, state) or (
                self._horizontal_reflection
                and states_equal_under_horizontal_reflection(existing, state)
            )
            if not equivalent:
                continue
            if existing_score <= score:
                return False
            self._entries[index] = (state, score)
            return True
        self._entries.append((state, score))
        return True


def enumerate_bounded_proof(
    goal: SearchGoal,
    *,
    max_score: int,
    reference: bool = False,
    horizontal_reflection: bool = False,
    terminal_step_test: Callable[[Candidate], bool] | None = None,
) -> ProofEnumeration:
    """逐层完整枚举，不接受状态上限、超时或启发式剪枝。

    ``reference=False`` 使用现有的摘要分桶和桶内精确确认；
    ``reference=True`` 使用线性精确候选去重和状态比较，供独立重放入口使用。
    两者的数学候选空间相同。
    """

    if max_score < 0:
        raise ValueError("max_score 不能为负数")

    candidate_generator: Callable[[GeometryState], tuple[Candidate, ...]]
    if reference:
        candidate_generator = _generate_candidates_reference
        state_index = _LinearExactStateIndex(
            horizontal_reflection=horizontal_reflection
        )
    else:
        candidate_generator = generate_candidates
        state_index = (
            HorizontalReflectionStateIndex()
            if horizontal_reflection
            else ExactStateIndex()
        )

    initial = SearchNode.initial()
    if not state_index.add_if_better(initial.state, initial.score):
        raise RuntimeError("初始状态不应被状态索引拒绝")
    frontier = (initial,)
    layers: list[ProofLayer] = []
    accepted_states = 1
    total_expanded = 0
    total_generated = 0
    total_equivalent_pruned = 0
    total_terminal_candidates = 0
    total_terminal_nonmatching_pruned = 0
    total_goal_tests = 0
    max_frontier = 1

    for score in range(max_score + 1):
        if any(node.score != score for node in frontier):
            raise RuntimeError("proof mode frontier 必须严格按 E-score 分层")

        goal_nodes = tuple(node for node in frontier if goal.reached(node.state))
        total_goal_tests += len(frontier)
        if goal_nodes:
            layers.append(
                ProofLayer(
                    score=score,
                    frontier_states=len(frontier),
                    goal_states=len(goal_nodes),
                    expanded_states=0,
                    generated_candidates=0,
                    accepted_next_states=0,
                    equivalent_pruned=0,
                    terminal_candidates=0,
                    terminal_nonmatching_pruned=0,
                )
            )
            return ProofEnumeration(
                status="found",
                minimum_score=score,
                layers=tuple(layers),
                expanded_states=total_expanded,
                generated_candidates=total_generated,
                accepted_states=accepted_states,
                equivalent_pruned=total_equivalent_pruned,
                terminal_candidates=total_terminal_candidates,
                terminal_nonmatching_pruned=total_terminal_nonmatching_pruned,
                max_frontier=max_frontier,
                goal_tests=total_goal_tests,
                node=goal_nodes[0],
            )

        if score == max_score:
            layers.append(
                ProofLayer(
                    score=score,
                    frontier_states=len(frontier),
                    goal_states=0,
                    expanded_states=0,
                    generated_candidates=0,
                    accepted_next_states=0,
                    equivalent_pruned=0,
                    terminal_candidates=0,
                    terminal_nonmatching_pruned=0,
                )
            )
            break

        next_frontier: list[SearchNode] = []
        generated_candidates = 0
        equivalent_pruned = 0
        terminal_candidates = 0
        terminal_nonmatching_pruned = 0
        terminal_cutoff = (
            terminal_step_test is not None and score + 1 == max_score
        )
        for node in frontier:
            for candidate in candidate_generator(node.state):
                generated_candidates += 1
                if terminal_cutoff:
                    if not terminal_step_test(candidate):
                        terminal_nonmatching_pruned += 1
                        continue
                    terminal_candidates += 1
                child = node.apply(candidate)
                if not state_index.add_if_better(child.state, child.score):
                    equivalent_pruned += 1
                    continue
                next_frontier.append(child)

        layers.append(
            ProofLayer(
                score=score,
                frontier_states=len(frontier),
                goal_states=0,
                expanded_states=len(frontier),
                generated_candidates=generated_candidates,
                accepted_next_states=len(next_frontier),
                equivalent_pruned=equivalent_pruned,
                terminal_candidates=terminal_candidates,
                terminal_nonmatching_pruned=terminal_nonmatching_pruned,
            )
        )
        total_expanded += len(frontier)
        total_generated += generated_candidates
        total_equivalent_pruned += equivalent_pruned
        total_terminal_candidates += terminal_candidates
        total_terminal_nonmatching_pruned += terminal_nonmatching_pruned
        accepted_states += len(next_frontier)
        frontier = tuple(next_frontier)
        max_frontier = max(max_frontier, len(frontier))

    return ProofEnumeration(
        status="exhausted",
        minimum_score=None,
        layers=tuple(layers),
        expanded_states=total_expanded,
        generated_candidates=total_generated,
        accepted_states=accepted_states,
        equivalent_pruned=total_equivalent_pruned,
        terminal_candidates=total_terminal_candidates,
        terminal_nonmatching_pruned=total_terminal_nonmatching_pruned,
        max_frontier=max_frontier,
        goal_tests=total_goal_tests,
    )


def build_bounded_proof(
    *,
    profile_path: str | Path,
    max_score: int,
    reference: bool = False,
) -> dict:
    """为固定正十七边形 profile 构造确定性的有界证明记录。"""

    profile = load_profile(profile_path)
    _require_supported_profile(profile.data["id"], profile.sha256)
    enumeration = enumerate_bounded_proof(
        Regular17Goal(),
        max_score=max_score,
        reference=reference,
        horizontal_reflection=True,
        terminal_step_test=is_regular17_terminal_step,
    )
    result = {
        "status": enumeration.status,
        "claim": (
            "no_target_at_or_below_max_score"
            if enumeration.status == "exhausted"
            else "target_found_at_minimum_score"
        ),
        "minimum_score": enumeration.minimum_score,
    }
    payload = {
        "schema": "euclid-min-bounded-proof/v1",
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "target": {
            "type": "regular_polygon_adjacent_vertex",
            "polygon_sides": 17,
            "accepted": ["B_plus", "B_minus"],
        },
        "proof_mode": {
            "strategy": "exact_breadth_first",
            "arithmetic": "sage_aa_exact",
            "candidate_generation": "all_distinct_objects_from_all_state_points",
            "heuristic_pruning": False,
            "state_limit": None,
            "timeouts": False,
            "safe_reductions": [
                "duplicate_draw_dominance",
                "same_object_parameterization_equivalence",
                "exact_state_equivalence",
                "horizontal_reflection_equivalence",
                "final_step_target_incidence",
            ],
        },
        "bound": {"metric": "e_move", "max_score": max_score},
        "result": result,
        "layers": [asdict(layer) for layer in enumeration.layers],
        "totals": {
            "expanded_states": enumeration.expanded_states,
            "generated_candidates": enumeration.generated_candidates,
            "accepted_states": enumeration.accepted_states,
            "equivalent_pruned": enumeration.equivalent_pruned,
            "terminal_candidates": enumeration.terminal_candidates,
            "terminal_nonmatching_pruned": (
                enumeration.terminal_nonmatching_pruned
            ),
            "max_frontier": enumeration.max_frontier,
            "goal_tests": enumeration.goal_tests,
        },
    }
    _validate_schema_instance(
        payload,
        _load_schema(DEFAULT_PROOF_SCHEMA),
        "proof_schema_invalid",
    )
    return payload


def save_bounded_proof(
    path: str | Path,
    *,
    profile_path: str | Path,
    max_score: int,
) -> dict:
    """生成并保存证明记录。"""

    payload = build_bounded_proof(
        profile_path=profile_path,
        max_score=max_score,
    )
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def check_bounded_proof(
    path: str | Path,
    *,
    profile_path: str | Path,
    schema_path: str | Path = DEFAULT_PROOF_SCHEMA,
) -> dict:
    """用无摘要的参考枚举器重放并核对一份证明记录。"""

    proof_path = Path(path)
    try:
        raw = proof_path.read_bytes()
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(
            "proof_json_invalid",
            f"无法读取 bounded proof: {error}",
        ) from error

    _validate_schema_instance(
        data,
        _load_schema(schema_path),
        "proof_schema_invalid",
    )
    profile = load_profile(profile_path)
    _require_supported_profile(profile.data["id"], profile.sha256)
    if data["profile"] != {
        "id": profile.data["id"],
        "sha256": profile.sha256,
    }:
        raise VerificationError(
            "proof_profile_mismatch",
            "bounded proof 与加载的 profile 不一致",
        )

    replayed = build_bounded_proof(
        profile_path=profile_path,
        max_score=data["bound"]["max_score"],
        reference=True,
    )
    if replayed != data:
        path_parts, asserted, actual = _first_difference(data, replayed)
        raise VerificationError(
            "proof_replay_mismatch",
            "证明记录与参考精确枚举结果不一致",
            details={
                "instance_path": "/".join(str(part) for part in path_parts),
                "asserted": asserted,
                "actual": actual,
            },
        )
    return {
        "valid": True,
        "proof_sha256": hashlib.sha256(raw).hexdigest(),
        "profile": data["profile"],
        "bound": data["bound"],
        "result": data["result"],
        "checker": "linear_exact_reference_replay",
    }


def _generate_candidates_reference(state: GeometryState) -> tuple[Candidate, ...]:
    """不使用数值摘要的完整候选生成参考实现。"""

    points = tuple(sorted(state.points))
    known_objects: list[Drawable] = list(state.drawables)
    candidates: list[Candidate] = []

    def add_if_new(candidate: Drawable) -> bool:
        if any(
            type(existing) is type(candidate) and existing == candidate
            for existing in known_objects
        ):
            return False
        known_objects.append(candidate)
        return True

    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            if add_if_new(Line.through(first, second)):
                candidates.append(Candidate("line", first, second))

    for center in points:
        for through in points:
            if center == through:
                continue
            if add_if_new(Circle.through(center, through)):
                candidates.append(Candidate("circle", center, through))
    return tuple(candidates)


def _require_supported_profile(profile_id: str, profile_sha256: str) -> None:
    if (
        profile_id != SUPPORTED_PROFILE_ID
        or profile_sha256 != SUPPORTED_PROFILE_SHA256
    ):
        raise VerificationError(
            "unsupported_proof_profile",
            "proof mode v1 只支持已冻结的 regular-17-e-fixed-v1 profile",
            details={"profile_id": profile_id, "profile_sha256": profile_sha256},
        )


def _first_difference(first, second, path=()):
    if type(first) is not type(second):
        return path, first, second
    if isinstance(first, dict):
        if first.keys() != second.keys():
            return path, sorted(first), sorted(second)
        for key in first:
            if first[key] != second[key]:
                return _first_difference(first[key], second[key], (*path, key))
        return path, first, second
    if isinstance(first, list):
        if len(first) != len(second):
            return (*path, "length"), len(first), len(second)
        for index, (first_item, second_item) in enumerate(zip(first, second)):
            if first_item != second_item:
                return _first_difference(
                    first_item,
                    second_item,
                    (*path, index),
                )
        return path, first, second
    return path, first, second
