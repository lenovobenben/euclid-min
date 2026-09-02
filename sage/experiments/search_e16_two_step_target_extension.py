"""穷尽固定 16E 前缀的两笔目标扩展；支持并行分片、暂停和恢复。"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
from pathlib import Path
from time import perf_counter

from sage.version import version as sage_version

from euclid_min.canonical_json import sha256_hex
from euclid_min.geometry import Point
from euclid_min.geometry_algebra_ir import replay_full_closure
from euclid_min.replay import ProgramReplayer
from euclid_min.search.backward import (
    generate_regular17_terminal_candidates_direct,
    generate_regular17_terminal_candidates_using_new_points,
    regular17_targets_on_step,
    terminal_parameterizations_using_new_points,
)
from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import node_from_steps, steps_from_program
from euclid_min.search.model import Candidate
from euclid_min.search.sharded_checkpoint import (
    load_or_create_checkpoint,
    record_completed_shard,
    remaining_shard_ids,
    set_checkpoint_status,
)
from euclid_min.verifier import verify_files
from experiments.build_detemple_1991_improved import DEFAULT_PROFILE
from experiments.build_regular17_geometry_algebra_ir import (
    CERTIFICATE_PATH,
    OUTPUT_PATH as GA_IR_PATH,
    REPOSITORY_ROOT,
)
from experiments.search_e17_one_step_target_extension import (
    _point_reference,
    _program_prefix,
)


DEFAULT_CHECKPOINT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e16-two-step-target-extension-checkpoint-sage-10.7.json"
)
DEFAULT_SUMMARY = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e16-two-step-target-extension-sage-10.7.json"
)
DEFAULT_CANDIDATE = (
    REPOSITORY_ROOT / "candidates" / "regular-17-18e-fixed-e16-extension.json"
)
SEARCH_SCRIPT_PATH = Path(__file__).resolve()
BACKWARD_MODULE_PATH = (
    REPOSITORY_ROOT / "sage" / "euclid_min" / "search" / "backward.py"
)
CANDIDATES_MODULE_PATH = (
    REPOSITORY_ROOT / "sage" / "euclid_min" / "search" / "candidates.py"
)
CHECKPOINT_MODULE_PATH = (
    REPOSITORY_ROOT
    / "sage"
    / "euclid_min"
    / "search"
    / "sharded_checkpoint.py"
)
E17_HELPER_SCRIPT_PATH = (
    REPOSITORY_ROOT
    / "sage"
    / "experiments"
    / "search_e17_one_step_target_extension.py"
)


_WORKER_STATE = None
_WORKER_CANDIDATES: tuple[Candidate, ...] = ()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _apply_precursor(state, precursor: Candidate):
    child = state.clone()
    if precursor.op == "line":
        addition = child.draw_line(precursor.first, precursor.second)
    elif precursor.op == "circle":
        addition = child.draw_circle(precursor.first, precursor.second)
    else:
        raise ValueError(f"不支持的首步操作 {precursor.op!r}")
    if not addition.new_object:
        raise RuntimeError("首步候选没有产生不同新对象")
    return child, addition


def _search_precursor(state, precursor: Candidate, candidate_index: int) -> dict:
    started = perf_counter()
    direct_targets = regular17_targets_on_step(precursor)
    child, addition = _apply_precursor(state, precursor)
    if direct_targets:
        return {
            "precursor_candidate_index": candidate_index,
            "precursor_operation": precursor.op,
            "new_points": len(addition.new_points),
            "terminal_parameterizations": 0,
            "terminal_candidates": 0,
            "hits": [
                {
                    "precursor_candidate_index": candidate_index,
                    "terminal_candidate_index": None,
                    "targets": [target.value for target in direct_targets],
                }
            ],
            "elapsed_seconds": perf_counter() - started,
        }

    parameterizations = terminal_parameterizations_using_new_points(
        child, addition.new_points
    )
    terminals = generate_regular17_terminal_candidates_using_new_points(
        child, addition.new_points
    )
    hits = [
        {
            "precursor_candidate_index": candidate_index,
            "terminal_candidate_index": terminal_index,
            "targets": [
                target.value for target in regular17_targets_on_step(terminal)
            ],
            "terminal_operation": terminal.op,
            "new_terminal_inputs": sum(
                any(point == new_point for new_point in addition.new_points)
                for point in (terminal.first, terminal.second)
            ),
        }
        for terminal_index, terminal in enumerate(terminals)
    ]
    if any(not hit["targets"] for hit in hits):
        raise RuntimeError("受限终步生成器返回了不经过目标的对象")
    return {
        "precursor_candidate_index": candidate_index,
        "precursor_operation": precursor.op,
        "new_points": len(addition.new_points),
        "terminal_parameterizations": parameterizations,
        "terminal_candidates": len(terminals),
        "hits": hits,
        "elapsed_seconds": perf_counter() - started,
    }


def _initialize_worker(state, candidates: tuple[Candidate, ...]) -> None:
    global _WORKER_STATE, _WORKER_CANDIDATES
    _WORKER_STATE = state
    _WORKER_CANDIDATES = candidates


def _search_shard(specification: tuple[str, int, int]) -> dict:
    shard_id, start, stop = specification
    if _WORKER_STATE is None:
        raise RuntimeError("分片 worker 尚未初始化")
    started = perf_counter()
    rows = [
        _search_precursor(
            _WORKER_STATE,
            _WORKER_CANDIDATES[candidate_index],
            candidate_index,
        )
        for candidate_index in range(start, stop)
    ]
    return {
        "shard_id": shard_id,
        "range": [start, stop],
        "precursor_candidates": len(rows),
        "precursor_lines": sum(
            row["precursor_operation"] == "line" for row in rows
        ),
        "precursor_circles": sum(
            row["precursor_operation"] == "circle" for row in rows
        ),
        "new_points_total": sum(row["new_points"] for row in rows),
        "new_points_min": min(row["new_points"] for row in rows),
        "new_points_max": max(row["new_points"] for row in rows),
        "terminal_parameterizations": sum(
            row["terminal_parameterizations"] for row in rows
        ),
        "terminal_candidates": sum(row["terminal_candidates"] for row in rows),
        "hits": [hit for row in rows for hit in row["hits"]],
        "elapsed_seconds": perf_counter() - started,
    }


def _append_candidate_step(
    program: list[dict],
    candidate: Candidate,
    *,
    drawable_id: str,
    binding_prefix: str,
) -> list[dict]:
    full = replay_full_closure(program)
    first_reference, first_binding = _point_reference(
        full, candidate.first, generated_id=f"{binding_prefix}_1"
    )
    second_reference, second_binding = _point_reference(
        full, candidate.second, generated_id=f"{binding_prefix}_2"
    )
    extended = list(program)
    for binding in (first_binding, second_binding):
        if binding is not None:
            extended.append(binding)
    if candidate.op == "line":
        extended.append(
            {
                "id": drawable_id,
                "op": "line",
                "through": [first_reference, second_reference],
            }
        )
    else:
        extended.append(
            {
                "id": drawable_id,
                "op": "circle",
                "center": first_reference,
                "through": second_reference,
            }
        )
    return extended


def _build_candidate_certificate(
    certificate: dict,
    prefix_program: list[dict],
    state,
    candidates: tuple[Candidate, ...],
    hit: dict,
) -> dict:
    precursor = candidates[hit["precursor_candidate_index"]]
    program = _append_candidate_step(
        prefix_program,
        precursor,
        drawable_id="ir_precursor",
        binding_prefix="ir_precursor_input",
    )
    if hit["terminal_candidate_index"] is not None:
        child, addition = _apply_precursor(state, precursor)
        terminals = generate_regular17_terminal_candidates_using_new_points(
            child, addition.new_points
        )
        terminal = terminals[hit["terminal_candidate_index"]]
        program = _append_candidate_step(
            program,
            terminal,
            drawable_id="ir_terminal_target_object",
            binding_prefix="ir_terminal_input",
        )
    replay = ProgramReplayer().replay(program)
    expected_score = 17 if hit["terminal_candidate_index"] is None else 18
    if replay.e_move != expected_score or not replay.targets:
        raise RuntimeError("两步命中记录不能编译为有效证书")
    construction = {
        "id": f"regular-17-{expected_score}e-fixed-e16-extension",
        "title": f"Regular 17-gon {expected_score}E fixed-E16 extension",
        "description": (
            "Exact extension discovered from the complete finite-real "
            "intersection closure of the verified 16E prefix."
        ),
        "program": program,
    }
    return {
        "schema": "euclid-min-certificate/v1",
        "problem": certificate["problem"],
        "profile": certificate["profile"],
        "construction": construction,
        "assertions": {
            "score": {"metric": "e_move", "e_move": expected_score},
            "targets": [target.value for target in replay.targets],
            "claim": "verified_construction",
        },
        "software": {
            "producer": {
                "name": "euclid-min-e16-two-step-target-extension",
                "version": "1",
            }
        },
        "integrity": {"construction_sha256": sha256_hex(construction)},
    }


def _summary(
    *,
    checkpoint: dict,
    candidates: tuple[Candidate, ...],
    state,
    input_sha256: dict[str, str],
    candidate_path: str | None,
    candidate_valid: bool | None,
    elapsed_seconds: float,
) -> dict:
    shard_results = [
        item["result"] for item in checkpoint["progress"]["completed_shards"]
    ]
    hits = [hit for result in shard_results for hit in result["hits"]]
    remaining = remaining_shard_ids(checkpoint)
    exhausted = not remaining
    status = "found" if hits else ("exhausted_no_hit" if exhausted else "paused")
    return {
        "schema": "euclid-min-fixed-prefix-two-step-search/v1",
        "mode": "exact_fixed_prefix_exhaustive" if exhausted else "exact_partial",
        "source": {"input_sha256": input_sha256},
        "scope": {
            "prefix_e_move": 16,
            "extension_budget_e": 2,
            "prefix_points": len(state.points),
            "prefix_lines": len(state.lines),
            "prefix_circles": len(state.circles),
            "precursor_candidates": len(candidates),
            "terminal_restriction": (
                "parent_has_no_one_step_target_so_terminal_uses_at_least_one_precursor_point"
            ),
        },
        "progress": {
            "status": status,
            "exhausted": exhausted,
            "completed_shards": len(shard_results),
            "total_shards": len(checkpoint["task"]["shard_ids"]),
            "remaining_shards": len(remaining),
            "completed_precursor_candidates": sum(
                result["precursor_candidates"] for result in shard_results
            ),
        },
        "coverage": {
            "precursor_lines": sum(
                result["precursor_lines"] for result in shard_results
            ),
            "precursor_circles": sum(
                result["precursor_circles"] for result in shard_results
            ),
            "new_points_total": sum(
                result["new_points_total"] for result in shard_results
            ),
            "terminal_parameterizations": sum(
                result["terminal_parameterizations"] for result in shard_results
            ),
            "terminal_candidates": sum(
                result["terminal_candidates"] for result in shard_results
            ),
        },
        "result": {
            "successful_branches": len(hits),
            "first_hit": hits[0] if hits else None,
            "candidate_certificate": candidate_path,
            "candidate_certificate_valid": candidate_valid,
        },
        "checkpoint": {
            "schema": checkpoint["schema"],
            "task_signature": checkpoint["task"]["signature"],
            "revision": checkpoint["progress"]["revision"],
            "status": checkpoint["progress"]["status"],
        },
        "environment": {"sage_version": sage_version},
        "elapsed_seconds_this_invocation": elapsed_seconds,
        "interpretation": (
            "命中会由独立 verifier 生成有效上界；只有 exhausted_no_hit 才精确排除"
            "已验证固定 16E 前缀的全部两笔扩展。该有限结论不排除其他 16E 前缀，"
            "也不是全局 18E 下界。"
        ),
    }


def _write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(args) -> int:
    started = perf_counter()
    certificate = json.loads(args.certificate.read_text(encoding="utf-8"))
    prefix_program = _program_prefix(certificate["construction"]["program"], 16)
    state = node_from_steps(steps_from_program(prefix_program)).state
    if generate_regular17_terminal_candidates_direct(state):
        raise RuntimeError("固定 16E 父状态已经存在一步目标候选，受限终步归约不适用")
    candidates = generate_candidates(state)
    shard_ranges = [
        (start, min(start + args.shard_size, len(candidates)))
        for start in range(0, len(candidates), args.shard_size)
    ]
    shard_ids = [f"{index:04d}" for index in range(len(shard_ranges))]
    input_paths = (
        args.certificate,
        args.ga_ir,
        SEARCH_SCRIPT_PATH,
        BACKWARD_MODULE_PATH,
        CANDIDATES_MODULE_PATH,
        CHECKPOINT_MODULE_PATH,
        E17_HELPER_SCRIPT_PATH,
    )
    input_sha256 = {
        str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): _sha256_file(
            path
        )
        for path in input_paths
    }
    configuration = {
        "prefix_e_move": 16,
        "prefix_point_count": len(state.points),
        "precursor_order": "generate_candidates_exact_deduplicated",
        "precursor_candidate_count": len(candidates),
        "terminal_order": "exact_lexicographic_lines_then_ordered_circles",
        "terminal_restriction": (
            "parent_has_no_one_step_target_so_terminal_uses_at_least_one_precursor_point"
        ),
        "shard_size": args.shard_size,
        "targets": ["B_plus", "B_minus"],
        "parent_one_step_target_candidates": 0,
    }
    checkpoint = load_or_create_checkpoint(
        args.checkpoint,
        task_id="regular-17-e16-two-step-target-extension-v1",
        profile_path=args.profile,
        input_sha256=input_sha256,
        configuration=configuration,
        shard_ids=shard_ids,
    )
    if checkpoint["progress"]["status"] != "completed":
        checkpoint = set_checkpoint_status(args.checkpoint, checkpoint, "running")

    remaining = list(remaining_shard_ids(checkpoint))
    selected = remaining[: args.max_shards] if args.max_shards else remaining
    specifications = [
        (shard_id, *shard_ranges[int(shard_id)]) for shard_id in selected
    ]
    first_hit = None
    interrupted = False
    pool = None
    try:
        if specifications:
            context = multiprocessing.get_context("fork")
            pool = context.Pool(
                processes=min(args.workers, len(specifications)),
                initializer=_initialize_worker,
                initargs=(state, candidates),
            )
            for result in pool.imap_unordered(_search_shard, specifications, chunksize=1):
                shard_id = result.pop("shard_id")
                checkpoint = record_completed_shard(
                    args.checkpoint,
                    checkpoint,
                    shard_id=shard_id,
                    result=result,
                )
                completed = len(checkpoint["progress"]["completed_shards"])
                print(
                    json.dumps(
                        {
                            "event": "shard_complete",
                            "shard": shard_id,
                            "completed": completed,
                            "total": len(shard_ids),
                            "precursors": result["precursor_candidates"],
                            "terminal_parameterizations": result[
                                "terminal_parameterizations"
                            ],
                            "hits": len(result["hits"]),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                if result["hits"] and args.stop_on_hit:
                    first_hit = result["hits"][0]
                    pool.terminate()
                    break
            else:
                pool.close()
            pool.join()
            pool = None
    except KeyboardInterrupt:
        interrupted = True
        if pool is not None:
            pool.terminate()
            pool.join()
            pool = None
    except BaseException:
        if pool is not None:
            pool.terminate()
            pool.join()
        set_checkpoint_status(args.checkpoint, checkpoint, "paused")
        raise

    remaining_after = remaining_shard_ids(checkpoint)
    if remaining_after:
        checkpoint = set_checkpoint_status(args.checkpoint, checkpoint, "paused")
    else:
        checkpoint = set_checkpoint_status(args.checkpoint, checkpoint, "completed")

    all_hits = [
        hit
        for item in checkpoint["progress"]["completed_shards"]
        for hit in item["result"]["hits"]
    ]
    if first_hit is None and all_hits:
        first_hit = all_hits[0]
    candidate_path = None
    candidate_valid = None
    if first_hit is not None:
        candidate_certificate = _build_candidate_certificate(
            certificate,
            prefix_program,
            state,
            candidates,
            first_hit,
        )
        args.candidate.parent.mkdir(parents=True, exist_ok=True)
        args.candidate.write_text(
            json.dumps(candidate_certificate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        candidate_valid = verify_files(args.candidate, args.profile).valid
        if not candidate_valid:
            raise RuntimeError("搜索命中生成的证书未通过独立 verifier")
        candidate_path = str(args.candidate.relative_to(REPOSITORY_ROOT)).replace(
            "\\", "/"
        )

    summary = _summary(
        checkpoint=checkpoint,
        candidates=candidates,
        state=state,
        input_sha256=input_sha256,
        candidate_path=candidate_path,
        candidate_valid=candidate_valid,
        elapsed_seconds=perf_counter() - started,
    )
    _write_summary(args.summary, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if interrupted:
        return 130
    if summary["progress"]["status"] == "paused":
        return 3
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--certificate", type=Path, default=CERTIFICATE_PATH)
    parser.add_argument("--ga-ir", type=Path, default=GA_IR_PATH)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--shard-size", type=int, default=32)
    parser.add_argument("--max-shards", type=int)
    parser.add_argument(
        "--stop-on-hit",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args()
    if args.workers < 1 or args.shard_size < 1:
        parser.error("--workers 和 --shard-size 必须为正整数")
    if args.max_shards is not None and args.max_shards < 1:
        parser.error("--max-shards 必须为正整数")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
