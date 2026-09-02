"""固定 16E 前缀两笔搜索 v2：候选级持久化、可暂停恢复、未决关系不误判。"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import tempfile
from pathlib import Path
from time import perf_counter

from sage.version import version as sage_version

from euclid_min.canonical_json import sha256_hex
from euclid_min.replay import ProgramReplayer
from euclid_min.search.backward import (
    generate_regular17_terminal_candidates_direct,
    regular17_targets_on_step,
    terminal_parameterizations_using_new_points,
)
from euclid_min.search.candidates import generate_candidates
from euclid_min.search.durable_journal import (
    SCHEMA_ID as JOURNAL_SCHEMA_ID,
    append_event,
    file_sha256,
    load_or_create_journal,
    task_definition,
)
from euclid_min.search.export import node_from_steps, steps_from_program
from euclid_min.search.incidence import (
    generate_terminal_candidates_with_deferred_incidence,
    new_points_on_existing_drawable,
)
from euclid_min.search.model import Candidate
from euclid_min.search.sharded_checkpoint import load_checkpoint
from euclid_min.verifier import verify_files
from experiments.build_detemple_1991_improved import DEFAULT_PROFILE
from experiments.build_regular17_geometry_algebra_ir import (
    CERTIFICATE_PATH,
    OUTPUT_PATH as GA_IR_PATH,
    REPOSITORY_ROOT,
)
from experiments.search_e16_two_step_target_extension import (
    BACKWARD_MODULE_PATH,
    CANDIDATES_MODULE_PATH,
    DEFAULT_CANDIDATE,
    DEFAULT_CHECKPOINT as LEGACY_CHECKPOINT,
    E17_HELPER_SCRIPT_PATH,
    SEARCH_SCRIPT_PATH as LEGACY_SEARCH_SCRIPT_PATH,
    _apply_precursor,
    _append_candidate_step,
    _program_prefix,
)


DEFAULT_JOURNAL = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e16-two-step-target-extension-checkpoint-v2-sage-10.7.jsonl"
)
DEFAULT_SUMMARY = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e16-two-step-target-extension-v2-sage-10.7.json"
)
SEARCH_SCRIPT_PATH = Path(__file__).resolve()
INCIDENCE_MODULE_PATH = (
    REPOSITORY_ROOT / "sage" / "euclid_min" / "search" / "incidence.py"
)
JOURNAL_MODULE_PATH = (
    REPOSITORY_ROOT / "sage" / "euclid_min" / "search" / "durable_journal.py"
)


_WORKER_STATE = None
_WORKER_CANDIDATES: tuple[Candidate, ...] = ()


def _initialize_worker(state, candidates: tuple[Candidate, ...]) -> None:
    global _WORKER_STATE, _WORKER_CANDIDATES
    _WORKER_STATE = state
    _WORKER_CANDIDATES = candidates


def _search_precursor(state, precursor: Candidate, candidate_index: int) -> dict:
    started = perf_counter()
    child, addition = _apply_precursor(state, precursor)
    direct_targets = regular17_targets_on_step(precursor)
    if direct_targets:
        return {
            "candidate_index": candidate_index,
            "precursor_operation": precursor.op,
            "new_points": len(addition.new_points),
            "terminal_parameterizations": 0,
            "terminal_candidates": 0,
            "deferred": [],
            "audit": {},
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
    unit_circle_points = new_points_on_existing_drawable(
        state,
        addition,
        state.circles[0],
    )
    generated = generate_terminal_candidates_with_deferred_incidence(
        child,
        addition.new_points,
        new_unit_circle_points=unit_circle_points,
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
                any(point is new_point for new_point in addition.new_points)
                for point in (terminal.first, terminal.second)
            ),
        }
        for terminal_index, terminal in enumerate(generated.candidates)
    ]
    if any(not hit["targets"] for hit in hits):
        raise RuntimeError("区间终步生成器返回了不经过目标的对象")
    return {
        "candidate_index": candidate_index,
        "precursor_operation": precursor.op,
        "new_points": len(addition.new_points),
        "terminal_parameterizations": parameterizations,
        "terminal_candidates": len(generated.candidates),
        "deferred": [item.as_dict() for item in generated.deferred],
        "audit": generated.audit.as_dict(),
        "hits": hits,
        "elapsed_seconds": perf_counter() - started,
    }


def _worker(candidate_index: int) -> dict:
    if _WORKER_STATE is None:
        raise RuntimeError("worker 尚未初始化")
    return _search_precursor(
        _WORKER_STATE,
        _WORKER_CANDIDATES[candidate_index],
        candidate_index,
    )


def _build_candidate_certificate_v2(
    certificate: dict,
    prefix_program: list[dict],
    state,
    candidates: tuple[Candidate, ...],
    hit: dict,
) -> dict:
    """从 v2 的区间生成顺序重放命中，并生成可独立验证的证书。"""

    precursor = candidates[hit["precursor_candidate_index"]]
    program = _append_candidate_step(
        prefix_program,
        precursor,
        drawable_id="ir_precursor",
        binding_prefix="ir_precursor_input",
    )
    if hit["terminal_candidate_index"] is not None:
        child, addition = _apply_precursor(state, precursor)
        unit_circle_points = new_points_on_existing_drawable(
            state,
            addition,
            state.circles[0],
        )
        generated = generate_terminal_candidates_with_deferred_incidence(
            child,
            addition.new_points,
            new_unit_circle_points=unit_circle_points,
        )
        terminal = generated.candidates[hit["terminal_candidate_index"]]
        program = _append_candidate_step(
            program,
            terminal,
            drawable_id="ir_terminal_target_object",
            binding_prefix="ir_terminal_input",
        )
    replay = ProgramReplayer().replay(program)
    expected_score = 17 if hit["terminal_candidate_index"] is None else 18
    if replay.e_move != expected_score or not replay.targets:
        raise RuntimeError("v2 命中不能重放为有效证书")
    construction = {
        "id": f"regular-17-{expected_score}e-fixed-e16-extension",
        "title": f"Regular 17-gon {expected_score}E fixed-E16 extension",
        "description": (
            "Exact extension discovered from the verified fixed 16E prefix."
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
                "name": "euclid-min-e16-two-step-target-extension-v2",
                "version": "2",
            }
        },
        "integrity": {"construction_sha256": sha256_hex(construction)},
    }


def _legacy_import_payload(path: Path, candidate_count: int) -> dict | None:
    if not path.exists():
        return None
    checkpoint = load_checkpoint(path)
    task = checkpoint["task"]
    configuration = task["configuration"]
    if configuration.get("prefix_e_move") != 16:
        raise RuntimeError("旧检查点不是固定 16E 搜索")
    if configuration.get("precursor_candidate_count") != candidate_count:
        raise RuntimeError("旧检查点候选数与 v2 不一致")
    ranges: list[list[int]] = []
    results = []
    for item in checkpoint["progress"]["completed_shards"]:
        result = item["result"]
        start, stop = result["range"]
        if not (0 <= start < stop <= candidate_count):
            raise RuntimeError("旧检查点含无效候选范围")
        if result["hits"]:
            raise RuntimeError("旧检查点已经含命中，应先独立处理")
        ranges.append([start, stop])
        results.append(result)
    covered = [index for start, stop in ranges for index in range(start, stop)]
    if len(covered) != len(set(covered)):
        raise RuntimeError("旧检查点候选范围重叠")
    if not ranges:
        return None
    return {
        "source_path": str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"),
        "source_sha256": file_sha256(path),
        "source_task_signature": task["signature"],
        "ranges": ranges,
        "completed_candidates": len(covered),
        "aggregate": {
            "precursor_lines": sum(item["precursor_lines"] for item in results),
            "precursor_circles": sum(
                item["precursor_circles"] for item in results
            ),
            "new_points_total": sum(item["new_points_total"] for item in results),
            "terminal_parameterizations": sum(
                item["terminal_parameterizations"] for item in results
            ),
            "terminal_candidates": sum(
                item["terminal_candidates"] for item in results
            ),
            "deferred_relations": 0,
            "structural_existing_objects": 0,
        },
    }


def _journal_state(snapshot, candidate_count: int) -> dict:
    completed: set[int] = set()
    rows: list[dict] = []
    imports: list[dict] = []
    last_status = "created"
    for event in snapshot.events:
        payload = event["payload"]
        if event["type"] == "legacy_import":
            imports.append(payload)
            for start, stop in payload["ranges"]:
                for candidate_index in range(start, stop):
                    if candidate_index in completed:
                        raise RuntimeError("日志导入范围重复")
                    completed.add(candidate_index)
        elif event["type"] == "result":
            candidate_index = payload["candidate_index"]
            if not 0 <= candidate_index < candidate_count:
                raise RuntimeError("日志结果候选编号越界")
            if candidate_index in completed:
                raise RuntimeError("日志含重复候选结果")
            completed.add(candidate_index)
            rows.append(payload)
        elif event["type"] == "status":
            last_status = payload["status"]
        else:
            raise RuntimeError(f"不支持的日志事件 {event['type']!r}")
    return {
        "completed": completed,
        "rows": rows,
        "imports": imports,
        "last_status": last_status,
    }


def _coverage(journal_state: dict) -> dict:
    keys = (
        "precursor_lines",
        "precursor_circles",
        "new_points_total",
        "terminal_parameterizations",
        "terminal_candidates",
        "deferred_relations",
        "structural_existing_objects",
    )
    totals = {key: 0 for key in keys}
    for imported in journal_state["imports"]:
        for key in keys:
            totals[key] += imported["aggregate"].get(key, 0)
    for row in journal_state["rows"]:
        totals["precursor_lines"] += row["precursor_operation"] == "line"
        totals["precursor_circles"] += row["precursor_operation"] == "circle"
        totals["new_points_total"] += row["new_points"]
        totals["terminal_parameterizations"] += row["terminal_parameterizations"]
        totals["terminal_candidates"] += row["terminal_candidates"]
        totals["deferred_relations"] += len(row["deferred"])
        totals["structural_existing_objects"] += row["audit"].get(
            "structural_existing_objects", 0
        )
    return totals


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _summary(
    *,
    snapshot,
    journal_state: dict,
    state,
    candidate_count: int,
    input_sha256: dict[str, str],
    elapsed_seconds: float,
    status: str,
) -> dict:
    completed_count = len(journal_state["completed"])
    coverage = _coverage(journal_state)
    hits = [hit for row in journal_state["rows"] for hit in row["hits"]]
    scan_complete = completed_count == candidate_count
    exhausted = scan_complete and not hits and coverage["deferred_relations"] == 0
    return {
        "schema": "euclid-min-fixed-prefix-two-step-search/v2",
        "mode": "exact_fixed_prefix_exhaustive" if exhausted else "exact_partial",
        "source": {
            "input_sha256": input_sha256,
            "legacy_imports": journal_state["imports"],
        },
        "scope": {
            "prefix_e_move": 16,
            "extension_budget_e": 2,
            "prefix_points": len(state.points),
            "prefix_lines": len(state.lines),
            "prefix_circles": len(state.circles),
            "precursor_candidates": candidate_count,
            "terminal_restriction": (
                "parent_has_no_one_step_target_so_terminal_uses_at_least_one_precursor_point"
            ),
        },
        "progress": {
            "status": status,
            "scan_complete": scan_complete,
            "exhausted": exhausted,
            "completed_precursor_candidates": completed_count,
            "remaining_precursor_candidates": candidate_count - completed_count,
            "durable_events": len(snapshot.events),
            "checkpoint_granularity": "one_precursor_candidate",
        },
        "coverage": coverage,
        "result": {
            "successful_branches": len(hits),
            "first_hit": hits[0] if hits else None,
            "unresolved_relations": coverage["deferred_relations"],
        },
        "checkpoint": {
            "schema": JOURNAL_SCHEMA_ID,
            "task_signature": snapshot.task["signature"],
            "last_event_sha256": snapshot.last_hash,
            "status": status,
        },
        "environment": {"sage_version": sage_version},
        "elapsed_seconds_this_invocation": elapsed_seconds,
        "interpretation": (
            "每个首步候选完成后立即追加并 fsync；中断或死机后最多重算当前正在执行的候选。"
            "区间未决关系保存在日志中，不作为否定结论。只有扫描完成、无命中且未决关系为零时，"
            "才精确排除该固定 16E 前缀的全部两笔扩展；这不是全局 18E 下界。"
        ),
    }


def run(args) -> int:
    started = perf_counter()
    certificate = json.loads(args.certificate.read_text(encoding="utf-8"))
    prefix_program = _program_prefix(certificate["construction"]["program"], 16)
    state = node_from_steps(steps_from_program(prefix_program)).state
    if generate_regular17_terminal_candidates_direct(state):
        raise RuntimeError("固定 16E 状态已有一步目标候选，受限归约不适用")
    candidates = generate_candidates(state)

    input_paths = (
        args.profile,
        args.certificate,
        args.ga_ir,
        SEARCH_SCRIPT_PATH,
        LEGACY_SEARCH_SCRIPT_PATH,
        E17_HELPER_SCRIPT_PATH,
        BACKWARD_MODULE_PATH,
        CANDIDATES_MODULE_PATH,
        INCIDENCE_MODULE_PATH,
        JOURNAL_MODULE_PATH,
    )
    input_sha256 = {
        str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): file_sha256(
            path
        )
        for path in input_paths
    }
    task = task_definition(
        task_id="regular-17-e16-two-step-target-extension-v2",
        input_sha256=input_sha256,
        configuration={
            "prefix_e_move": 16,
            "precursor_candidate_count": len(candidates),
            "terminal_test": "strict_real_intervals_with_explicit_deferred_relations",
            "checkpoint_granularity": "one_precursor_candidate",
            "targets": ["B_plus", "B_minus"],
        },
        work_ids=(f"{index:05d}" for index in range(len(candidates))),
    )
    snapshot = load_or_create_journal(args.journal, task=task)
    journal_state = _journal_state(snapshot, len(candidates))
    if not snapshot.events:
        imported = _legacy_import_payload(args.legacy_checkpoint, len(candidates))
        if imported is not None:
            snapshot = append_event(
                args.journal,
                snapshot,
                event_type="legacy_import",
                payload=imported,
            )
            journal_state = _journal_state(snapshot, len(candidates))
            print(
                json.dumps(
                    {
                        "event": "legacy_import",
                        "completed_candidates": imported["completed_candidates"],
                        "ranges": imported["ranges"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    snapshot = append_event(
        args.journal,
        snapshot,
        event_type="status",
        payload={"status": "running"},
    )
    completed = journal_state["completed"]
    remaining = [
        index for index in range(len(candidates)) if index not in completed
    ]
    selected = (
        remaining[: args.max_candidates] if args.max_candidates else remaining
    )
    pool = None
    interrupted = False
    stop_requested = False
    new_rows: list[dict] = []
    try:
        if selected:
            context = multiprocessing.get_context("fork")
            pool = context.Pool(
                processes=min(args.workers, len(selected)),
                initializer=_initialize_worker,
                initargs=(state, candidates),
            )
            for row in pool.imap_unordered(_worker, selected, chunksize=1):
                snapshot = append_event(
                    args.journal,
                    snapshot,
                    event_type="result",
                    payload=row,
                )
                new_rows.append(row)
                completed.add(row["candidate_index"])
                print(
                    json.dumps(
                        {
                            "event": "candidate_complete",
                            "candidate_index": row["candidate_index"],
                            "completed": len(completed),
                            "total": len(candidates),
                            "deferred": len(row["deferred"]),
                            "hits": len(row["hits"]),
                            "elapsed_seconds": row["elapsed_seconds"],
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                if row["hits"] and args.stop_on_hit:
                    stop_requested = True
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
        append_event(
            args.journal,
            snapshot,
            event_type="status",
            payload={"status": "paused_after_error"},
        )
        raise

    journal_state = _journal_state(snapshot, len(candidates))
    coverage = _coverage(journal_state)
    if stop_requested:
        status = "found"
    elif len(journal_state["completed"]) < len(candidates):
        status = "paused" if interrupted or args.max_candidates else "running"
    elif coverage["deferred_relations"]:
        status = "scan_complete_with_deferred"
    else:
        status = "completed"
    snapshot = append_event(
        args.journal,
        snapshot,
        event_type="status",
        payload={"status": status},
    )
    journal_state = _journal_state(snapshot, len(candidates))
    summary = _summary(
        snapshot=snapshot,
        journal_state=journal_state,
        state=state,
        candidate_count=len(candidates),
        input_sha256=input_sha256,
        elapsed_seconds=perf_counter() - started,
        status=status,
    )
    _atomic_json(args.summary, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

    hits = [hit for row in journal_state["rows"] for hit in row["hits"]]
    if hits:
        candidate = _build_candidate_certificate_v2(
            certificate,
            prefix_program,
            state,
            candidates,
            hits[0],
        )
        _atomic_json(args.candidate, candidate)
        if not verify_files(args.candidate, args.profile).valid:
            raise RuntimeError("v2 命中证书未通过独立 verifier")
    if interrupted:
        return 130
    if status in {"paused", "running", "scan_complete_with_deferred"}:
        return 3
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--certificate", type=Path, default=CERTIFICATE_PATH)
    parser.add_argument("--ga-ir", type=Path, default=GA_IR_PATH)
    parser.add_argument("--legacy-checkpoint", type=Path, default=LEGACY_CHECKPOINT)
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-candidates", type=int)
    parser.add_argument(
        "--stop-on-hit",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers 必须为正整数")
    if args.max_candidates is not None and args.max_candidates < 1:
        parser.error("--max-candidates 必须为正整数")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
