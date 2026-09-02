"""以候选级独立进程定位固定 E16+2 搜索中的高代价首步。"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import time
from pathlib import Path

from euclid_min.search.backward import generate_regular17_terminal_candidates_direct
from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import node_from_steps, steps_from_program
from euclid_min.search.sharded_checkpoint import (
    load_checkpoint,
    load_or_create_checkpoint,
    record_completed_shard,
    remaining_shard_ids,
    set_checkpoint_status,
)
from experiments.build_detemple_1991_improved import DEFAULT_PROFILE
from experiments.build_regular17_geometry_algebra_ir import (
    CERTIFICATE_PATH,
    REPOSITORY_ROOT,
)
from experiments.search_e16_two_step_target_extension import (
    DEFAULT_CHECKPOINT as MAIN_CHECKPOINT,
    SEARCH_SCRIPT_PATH as MAIN_SEARCH_SCRIPT,
    _program_prefix,
    _search_precursor,
)


DIAGNOSTIC_SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e16-two-step-stalled-candidate-diagnostic-sage-10.7.json"
)


_STATE = None
_CANDIDATES = ()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_process(candidate_index: int, result_queue) -> None:
    started = time.monotonic()
    try:
        result = _search_precursor(
            _STATE,
            _CANDIDATES[candidate_index],
            candidate_index,
        )
        result_queue.put(
            {
                "status": "exact_completed",
                "candidate_index": candidate_index,
                "result": result,
                "wall_seconds": time.monotonic() - started,
            }
        )
    except BaseException as error:
        result_queue.put(
            {
                "status": "error",
                "candidate_index": candidate_index,
                "error_type": type(error).__name__,
                "error": str(error),
                "wall_seconds": time.monotonic() - started,
            }
        )


def _selected_candidate_indices(
    main_checkpoint: dict,
    *,
    missing_shards: int,
) -> tuple[list[str], list[int]]:
    shard_ids = main_checkpoint["task"]["shard_ids"]
    completed = {
        item["id"] for item in main_checkpoint["progress"]["completed_shards"]
    }
    missing = [shard_id for shard_id in shard_ids if shard_id not in completed]
    selected_shards = missing[:missing_shards]
    shard_size = main_checkpoint["task"]["configuration"]["shard_size"]
    candidate_count = main_checkpoint["task"]["configuration"][
        "precursor_candidate_count"
    ]
    indices = []
    for shard_id in selected_shards:
        start = int(shard_id) * shard_size
        stop = min(start + shard_size, candidate_count)
        indices.extend(range(start, stop))
    return selected_shards, indices


def _summary(payload: dict) -> dict:
    rows = [
        item["result"] for item in payload["progress"]["completed_shards"]
    ]
    exact = [row for row in rows if row["status"] == "exact_completed"]
    timed_out = [row for row in rows if row["status"] == "timeout"]
    errors = [row for row in rows if row["status"] == "error"]
    hits = [
        hit
        for row in exact
        for hit in row["result"]["hits"]
    ]
    return {
        "schema": "euclid-min-e16-precursor-cost-diagnostic/v1",
        "mode": "diagnostic_not_exhaustive_proof",
        "task_signature": payload["task"]["signature"],
        "status": payload["progress"]["status"],
        "selected_candidates": len(payload["task"]["shard_ids"]),
        "exact_completed": len(exact),
        "timed_out": len(timed_out),
        "timeout_candidate_indices": [row["candidate_index"] for row in timed_out],
        "errors": len(errors),
        "successful_branches": len(hits),
        "interpretation": (
            "该文件只定位高代价首步；timeout 不是数学排除，必须改用保持精确性的"
            "替代判定后重新解决。"
        ),
    }


def run(args) -> int:
    global _STATE, _CANDIDATES
    main_checkpoint = load_checkpoint(args.main_checkpoint)
    selected_shards, candidate_indices = _selected_candidate_indices(
        main_checkpoint,
        missing_shards=args.missing_shards,
    )
    if not candidate_indices:
        print(json.dumps({"event": "nothing_to_diagnose"}))
        return 0

    certificate = json.loads(args.certificate.read_text(encoding="utf-8"))
    prefix_program = _program_prefix(certificate["construction"]["program"], 16)
    state = node_from_steps(steps_from_program(prefix_program)).state
    if generate_regular17_terminal_candidates_direct(state):
        raise RuntimeError("固定 E16 父状态意外存在一步目标候选")
    candidates = generate_candidates(state)
    if len(candidates) != main_checkpoint["task"]["configuration"][
        "precursor_candidate_count"
    ]:
        raise RuntimeError("重新生成的首步候选数量与主检查点不一致")
    _STATE = state
    _CANDIDATES = candidates

    input_sha256 = {
        str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): _sha256_file(
            path
        )
        for path in (
            args.certificate,
            args.main_checkpoint,
            MAIN_SEARCH_SCRIPT,
            DIAGNOSTIC_SCRIPT_PATH,
        )
    }
    configuration = {
        "main_task_signature": main_checkpoint["task"]["signature"],
        "selected_missing_shards": selected_shards,
        "candidate_indices": candidate_indices,
        "timeout_milliseconds": int(args.timeout_seconds * 1000),
        "process_isolation": "one_forked_process_per_candidate",
    }
    payload = load_or_create_checkpoint(
        args.output,
        task_id="regular-17-e16-stalled-precursor-diagnostic-v1",
        profile_path=args.profile,
        input_sha256=input_sha256,
        configuration=configuration,
        shard_ids=[f"candidate.{index:05d}" for index in candidate_indices],
    )
    payload = set_checkpoint_status(args.output, payload, "running")
    remaining = [
        int(shard_id.split(".")[1]) for shard_id in remaining_shard_ids(payload)
    ]

    context = multiprocessing.get_context("fork")
    active: dict[int, dict] = {}
    pending = iter(remaining)
    interrupted = False

    def start_one(candidate_index: int) -> None:
        queue = context.Queue(maxsize=1)
        process = context.Process(
            target=_candidate_process,
            args=(candidate_index, queue),
        )
        process.start()
        active[candidate_index] = {
            "process": process,
            "queue": queue,
            "started": time.monotonic(),
        }

    try:
        for _ in range(min(args.workers, len(remaining))):
            start_one(next(pending))
        pending_exhausted = len(active) == 0
        while active:
            finished = []
            for candidate_index, task in list(active.items()):
                process = task["process"]
                elapsed = time.monotonic() - task["started"]
                row = None
                if not process.is_alive():
                    process.join()
                    try:
                        row = task["queue"].get(timeout=1)
                    except Exception:
                        row = {
                            "status": "error",
                            "candidate_index": candidate_index,
                            "error_type": "MissingWorkerResult",
                            "error": f"worker exit code {process.exitcode}",
                            "wall_seconds": elapsed,
                        }
                elif elapsed >= args.timeout_seconds:
                    process.terminate()
                    process.join()
                    row = {
                        "status": "timeout",
                        "candidate_index": candidate_index,
                        "wall_seconds": elapsed,
                    }
                if row is None:
                    continue
                shard_id = f"candidate.{candidate_index:05d}"
                payload = record_completed_shard(
                    args.output,
                    payload,
                    shard_id=shard_id,
                    result=row,
                )
                print(
                    json.dumps(
                        {
                            "event": "candidate_diagnostic_complete",
                            "candidate_index": candidate_index,
                            "status": row["status"],
                            "wall_seconds": row["wall_seconds"],
                        }
                    ),
                    flush=True,
                )
                task["queue"].close()
                finished.append(candidate_index)
            for candidate_index in finished:
                del active[candidate_index]
                try:
                    start_one(next(pending))
                except StopIteration:
                    pending_exhausted = True
            if active and not finished:
                time.sleep(0.1)
        if not pending_exhausted:
            raise RuntimeError("诊断调度器没有消费全部候选")
    except KeyboardInterrupt:
        interrupted = True
        for task in active.values():
            task["process"].terminate()
            task["process"].join()
            task["queue"].close()

    if remaining_shard_ids(payload):
        payload = set_checkpoint_status(args.output, payload, "paused")
    else:
        payload = set_checkpoint_status(args.output, payload, "completed")
    summary = _summary(payload)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if interrupted:
        return 130
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--certificate", type=Path, default=CERTIFICATE_PATH)
    parser.add_argument("--main-checkpoint", type=Path, default=MAIN_CHECKPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--missing-shards", type=int, default=1)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args()
    if args.missing_shards < 1 or args.workers < 1 or args.timeout_seconds <= 0:
        parser.error("分片数、worker 数和超时必须为正")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
