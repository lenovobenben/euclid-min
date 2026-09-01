"""并行且可暂停恢复地搜索最后一条直线邻接既有目标圆点。"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import signal
from contextlib import contextmanager
from math import comb
from pathlib import Path

from final_pair_line_adjacent_search import (
    BALL_PRECISION,
    ball_candidate_may_reach_existing,
    ball_carrier,
    ball_line_carrier,
    exact_candidate_reaches_existing,
    exact_line_carrier,
    prepare_final_pair_adjacent_universe,
)
from final_pair_line_chord_search import deserialize_ball_point


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
FRONTIER_PATH = ROOT / "full-point-candidate-frontier-69e.json"
CACHE_PATH = ROOT / "tmp" / "m257-8-final-pair-point-balls.json"
CHECKPOINT_PATH = ROOT / "tmp" / "m257-8-final-pair-line-adjacent-parallel.json"
LOCK_PATH = ROOT / "tmp" / "m257-8-final-pair-line-adjacent-parallel.lock"
OUTPUT_PATH = ROOT / "final-pair-line-adjacent-search-68e.json"


_POINT_ITEMS = []
_BALL_POINTS = []
_EXACT_EXISTING_CARRIERS = []
_BALL_EXISTING_CARRIERS = []


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sources() -> dict:
    return {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": _sha256_file(CERTIFICATE_PATH),
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(
            FULL_CLOSURE_PATH
        ),
        "candidate_frontier_report": FRONTIER_PATH.name,
        "candidate_frontier_report_sha256": _sha256_file(FRONTIER_PATH),
    }


def _algorithm() -> dict:
    return {
        "runner_sha256": _sha256_file(Path(__file__).resolve()),
        "search_module_sha256": _sha256_file(
            ROOT / "final_pair_line_adjacent_search.py"
        ),
    }


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


@contextmanager
def _single_runner():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    for _attempt in range(2):
        try:
            descriptor = os.open(
                LOCK_PATH,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            try:
                old_pid = int(LOCK_PATH.read_text(encoding="ascii").strip())
                os.kill(old_pid, 0)
            except (OSError, ValueError):
                LOCK_PATH.unlink(missing_ok=True)
                continue
            raise RuntimeError(f"已有并行直线邻接搜索在运行：PID {old_pid}")
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        break
    else:
        raise RuntimeError("无法取得并行直线邻接搜索锁")
    try:
        yield
    finally:
        try:
            owner = int(LOCK_PATH.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            owner = -1
        if owner == os.getpid():
            LOCK_PATH.unlink(missing_ok=True)


def _load_point_balls(source: dict, point_ids: list[str]) -> list[tuple]:
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if cache["source"] != source or cache["point_ids"] != point_ids:
        raise ValueError("共享严格实球缓存与当前输入不一致")
    if cache["precision_bits"] != BALL_PRECISION:
        raise ValueError("共享严格实球缓存精度不一致")
    if cache["next_point_index"] != len(point_ids):
        raise ValueError("共享严格实球缓存尚未完成")
    return [deserialize_ball_point(value) for value in cache["balls"]]


def _pair_at(index: int, point_count: int) -> tuple[int, int]:
    """返回 itertools.combinations(range(n), 2) 的第 index 对。"""

    if index < 0 or index >= comb(point_count, 2):
        raise IndexError("点对索引越界")
    low = 0
    high = point_count - 1
    while low + 1 < high:
        middle = (low + high) // 2
        before = middle * (2 * point_count - middle - 1) // 2
        if before <= index:
            low = middle
        else:
            high = middle
    first = low
    before = first * (2 * point_count - first - 1) // 2
    second = first + 1 + (index - before)
    return first, second


def _chunk_bounds(chunk_index: int, chunk_size: int, total: int) -> tuple[int, int]:
    start = chunk_index * chunk_size
    return start, min(start + chunk_size, total)


def _process_chunk(task: tuple[int, int, int]) -> dict:
    chunk_index, chunk_size, total = task
    start, end = _chunk_bounds(chunk_index, chunk_size, total)
    point_count = len(_POINT_ITEMS)
    first_index, second_index = _pair_at(start, point_count)
    relation_checks = 0
    ball_excluded = 0
    exact_checks = 0
    solutions = []
    for definition_index in range(start, end):
        candidate_ball = ball_line_carrier(
            _BALL_POINTS[first_index],
            _BALL_POINTS[second_index],
        )
        may_hit, checks = ball_candidate_may_reach_existing(
            candidate_ball,
            _BALL_EXISTING_CARRIERS,
        )
        relation_checks += checks
        if may_hit:
            exact_checks += 1
            candidate_exact = exact_line_carrier(
                _POINT_ITEMS[first_index][1],
                _POINT_ITEMS[second_index][1],
            )
            hits = exact_candidate_reaches_existing(
                candidate_exact,
                _EXACT_EXISTING_CARRIERS,
            )
            if hits:
                solutions.append(
                    {
                        "definition_index": definition_index,
                        "through": [
                            _POINT_ITEMS[first_index][0],
                            _POINT_ITEMS[second_index][0],
                        ],
                        "hits": hits,
                    }
                )
        else:
            ball_excluded += 1
        second_index += 1
        if second_index >= point_count:
            first_index += 1
            second_index = first_index + 1
    return {
        "chunk_index": chunk_index,
        "definitions_tested": end - start,
        "ball_relation_checks": relation_checks,
        "ball_excluded_definitions": ball_excluded,
        "exact_checks": exact_checks,
        "solutions": solutions,
    }


def _load_checkpoint(source: dict, total: int, chunk_size: int) -> dict:
    chunk_count = (total + chunk_size - 1) // chunk_size
    if not CHECKPOINT_PATH.exists():
        return {
            "schema": "euclid-min-regular-257-final-pair-line-adjacent-parallel-checkpoint/v1",
            "source": source,
            "algorithm": _algorithm(),
            "total_definitions": total,
            "chunk_size": chunk_size,
            "chunk_count": chunk_count,
            "completed_chunks": {},
            "stage": "definitions",
        }
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    if checkpoint["source"] != source:
        raise ValueError("搜索检查点输入摘要不一致")
    if checkpoint["algorithm"] != _algorithm():
        raise ValueError("搜索检查点由不同版本算法生成")
    if checkpoint["total_definitions"] != total:
        raise ValueError("搜索检查点定义总数不一致")
    if checkpoint["chunk_size"] != chunk_size:
        raise ValueError("续跑必须使用与检查点相同的 chunk-size")
    if checkpoint["chunk_count"] != chunk_count:
        raise ValueError("搜索检查点分块总数不一致")
    return checkpoint


def _aggregate(checkpoint: dict) -> dict:
    ordered = [
        checkpoint["completed_chunks"][str(index)]
        for index in range(checkpoint["chunk_count"])
    ]
    solutions = sorted(
        (solution for chunk in ordered for solution in chunk["solutions"]),
        key=lambda solution: solution["definition_index"],
    )
    return {
        "definitions_tested": sum(
            chunk["definitions_tested"] for chunk in ordered
        ),
        "ball_relation_checks": sum(
            chunk["ball_relation_checks"] for chunk in ordered
        ),
        "ball_excluded_definitions": sum(
            chunk["ball_excluded_definitions"] for chunk in ordered
        ),
        "exact_checks": sum(chunk["exact_checks"] for chunk in ordered),
        "solutions": solutions,
        "solutions_found": len(solutions),
        "status": "solution_found" if solutions else "exhausted_no_solution",
    }


def run(
    *,
    workers: int,
    chunk_size: int,
    max_chunks: int | None,
) -> dict | None:
    global _POINT_ITEMS
    global _BALL_POINTS
    global _EXACT_EXISTING_CARRIERS
    global _BALL_EXISTING_CARRIERS

    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    frontier = json.loads(FRONTIER_PATH.read_text(encoding="utf-8"))
    source = _sources()
    universe = prepare_final_pair_adjacent_universe(
        certificate,
        frontier,
        trace=lambda message: print(message, flush=True),
    )
    _POINT_ITEMS = universe["point_items"]
    _BALL_POINTS = _load_point_balls(
        source,
        [name for name, _point in _POINT_ITEMS],
    )
    _EXACT_EXISTING_CARRIERS = universe["existing_target_carriers"]
    _BALL_EXISTING_CARRIERS = [
        ball_carrier(carrier) for _name, carrier in _EXACT_EXISTING_CARRIERS
    ]
    total = comb(len(_POINT_ITEMS), 2)
    checkpoint = _load_checkpoint(source, total, chunk_size)
    if checkpoint["stage"] == "complete" and OUTPUT_PATH.exists():
        return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    pending = [
        index
        for index in range(checkpoint["chunk_count"])
        if str(index) not in checkpoint["completed_chunks"]
    ]
    if max_chunks is not None:
        pending = pending[:max_chunks]
    tasks = [
        (index, checkpoint["chunk_size"], checkpoint["total_definitions"])
        for index in pending
    ]
    if tasks:
        context = multiprocessing.get_context("fork")
        with context.Pool(processes=workers) as pool:
            for result in pool.imap_unordered(_process_chunk, tasks, chunksize=1):
                key = str(result["chunk_index"])
                checkpoint["completed_chunks"][key] = result
                _write_json_atomic(CHECKPOINT_PATH, checkpoint)
                print(
                    f"chunks={len(checkpoint['completed_chunks'])}/"
                    f"{checkpoint['chunk_count']} last={result['chunk_index']} "
                    f"exact_checks={result['exact_checks']} "
                    f"solutions={len(result['solutions'])}",
                    flush=True,
                )
    if len(checkpoint["completed_chunks"]) < checkpoint["chunk_count"]:
        print(f"paused_checkpoint={CHECKPOINT_PATH}", flush=True)
        return None

    search = _aggregate(checkpoint)
    report = {
        "schema": "euclid-min-regular-257-final-pair-line-adjacent-search/v1",
        "source": source,
        "semantics": {
            "removed_paid_drawables": universe["removed"],
            "candidate_e_move": 68,
            "candidate_family": (
                "one_line_through_two_available_materialized_exact_points"
            ),
            "target_event": (
                "a_new_candidate_intersection_on_c0_is_adjacent_to_an_"
                "already_available_point_on_c0"
            ),
            "limitations": [
                "本报告与目标弦报告合并后才完整覆盖该分片的直线候选。",
                "尚未检查圆候选，也未物化 474 个抽象残余圆交点。",
            ],
        },
        "universe": {
            "available_points": universe["available_points"],
            "available_exact_coordinate_points": len(_POINT_ITEMS),
            "existing_target_carriers": len(_EXACT_EXISTING_CARRIERS),
            "line_definitions": total,
        },
        "parallelization": {
            "workers": workers,
            "chunk_size": checkpoint["chunk_size"],
            "chunk_count": checkpoint["chunk_count"],
        },
        "search": search,
    }
    _write_json_atomic(OUTPUT_PATH, report)
    checkpoint["stage"] = "complete"
    checkpoint["output"] = OUTPUT_PATH.name
    _write_json_atomic(CHECKPOINT_PATH, checkpoint)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--max-chunks", type=int)
    args = parser.parse_args()
    if args.workers <= 0 or args.chunk_size <= 0:
        raise ValueError("workers 和 chunk-size 必须为正数")

    def interrupt(_signal_number, _frame) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        with _single_runner():
            report = run(
                workers=args.workers,
                chunk_size=args.chunk_size,
                max_chunks=args.max_chunks,
            )
    except KeyboardInterrupt:
        print(f"interrupted_checkpoint={CHECKPOINT_PATH}", flush=True)
        return
    if report is None:
        return
    print(f"wrote={OUTPUT_PATH}")
    print(f"solutions_found={report['search']['solutions_found']}")


if __name__ == "__main__":
    main()
