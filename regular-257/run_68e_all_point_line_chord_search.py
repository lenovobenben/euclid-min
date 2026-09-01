"""并行搜索最大前沿全部 2103 个可用点定义的目标弦直线。"""

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

from final_pair_line_chord_search import (
    BALL_PRECISION,
    ball_line_chord_may_hit,
    deserialize_ball_point,
)


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
FRONTIER_PATH = ROOT / "full-point-candidate-frontier-69e.json"
POINT_AUDIT_PATH = ROOT / "residual-point-ball-audit-68e.json"
CACHE_PATH = ROOT / "tmp" / "m257-8-final-pair-all-point-balls.json"
CHECKPOINT_PATH = ROOT / "tmp" / "m257-8-all-point-line-chord-parallel.json"
LOCK_PATH = ROOT / "tmp" / "m257-8-all-point-line-chord-parallel.lock"
OUTPUT_PATH = ROOT / "all-point-line-chord-search-68e.json"


_POINT_IDS: list[str] = []
_BALL_POINTS: list[tuple] = []


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_sources() -> dict:
    return {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": _sha256_file(CERTIFICATE_PATH),
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(FULL_CLOSURE_PATH),
        "candidate_frontier_report": FRONTIER_PATH.name,
        "candidate_frontier_report_sha256": _sha256_file(FRONTIER_PATH),
    }


def _sources() -> dict:
    return {
        **_base_sources(),
        "residual_point_ball_audit": POINT_AUDIT_PATH.name,
        "residual_point_ball_audit_sha256": _sha256_file(POINT_AUDIT_PATH),
    }


def _algorithm() -> dict:
    return {
        "runner_sha256": _sha256_file(Path(__file__).resolve()),
        "line_chord_module_sha256": _sha256_file(
            ROOT / "final_pair_line_chord_search.py"
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
            raise RuntimeError(f"已有全部点目标弦搜索在运行：PID {old_pid}")
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        break
    else:
        raise RuntimeError("无法取得全部点目标弦搜索锁")
    try:
        yield
    finally:
        try:
            owner = int(LOCK_PATH.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            owner = -1
        if owner == os.getpid():
            LOCK_PATH.unlink(missing_ok=True)


def _load_point_cache() -> tuple[list[str], list[tuple]]:
    audit = json.loads(POINT_AUDIT_PATH.read_text(encoding="utf-8"))
    if audit["audit"]["status"] != "complete":
        raise ValueError("抽象残余点实球审计尚未完成")
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if cache["source"] != _base_sources():
        raise ValueError("全部点实球缓存的输入摘要不一致")
    if cache["precision_bits"] != BALL_PRECISION:
        raise ValueError("全部点实球缓存精度不一致")
    if len(cache["point_ids"]) != audit["universe"]["available_points"]:
        raise ValueError("全部点实球缓存点数不一致")
    if len(cache["balls"]) != len(cache["point_ids"]):
        raise ValueError("全部点实球缓存尚未完成")
    return cache["point_ids"], [
        deserialize_ball_point(value) for value in cache["balls"]
    ]


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
    second = first + 1 + index - before
    return first, second


def _process_chunk(task: tuple[int, int, int]) -> dict:
    chunk_index, chunk_size, total = task
    start = chunk_index * chunk_size
    end = min(start + chunk_size, total)
    point_count = len(_POINT_IDS)
    first_index, second_index = _pair_at(start, point_count)
    excluded = 0
    unresolved = []
    for definition_index in range(start, end):
        if ball_line_chord_may_hit(
            _BALL_POINTS[first_index],
            _BALL_POINTS[second_index],
        ):
            unresolved.append(
                {
                    "definition_index": definition_index,
                    "through": [
                        _POINT_IDS[first_index],
                        _POINT_IDS[second_index],
                    ],
                }
            )
        else:
            excluded += 1
        second_index += 1
        if second_index >= point_count:
            first_index += 1
            second_index = first_index + 1
    return {
        "chunk_index": chunk_index,
        "definitions_tested": end - start,
        "ball_excluded_definitions": excluded,
        "unresolved": unresolved,
    }


def _load_checkpoint(source: dict, total: int, chunk_size: int) -> dict:
    chunk_count = (total + chunk_size - 1) // chunk_size
    if not CHECKPOINT_PATH.exists():
        return {
            "schema": "euclid-min-regular-257-all-point-line-chord-checkpoint/v1",
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
    return checkpoint


def _aggregate(checkpoint: dict) -> dict:
    ordered = [
        checkpoint["completed_chunks"][str(index)]
        for index in range(checkpoint["chunk_count"])
    ]
    unresolved = sorted(
        (item for chunk in ordered for item in chunk["unresolved"]),
        key=lambda item: item["definition_index"],
    )
    tested = sum(chunk["definitions_tested"] for chunk in ordered)
    excluded = sum(chunk["ball_excluded_definitions"] for chunk in ordered)
    return {
        "definitions_tested": tested,
        "ball_excluded_definitions": excluded,
        "unresolved_definitions": unresolved,
        "unresolved_count": len(unresolved),
        "solutions_found": 0 if not unresolved else None,
        "status": (
            "exhausted_no_solution"
            if not unresolved
            else "exhausted_with_unresolved_definitions"
        ),
    }


def run(*, workers: int, chunk_size: int, max_chunks: int | None) -> dict | None:
    global _POINT_IDS, _BALL_POINTS
    _POINT_IDS, _BALL_POINTS = _load_point_cache()
    source = _sources()
    total = comb(len(_POINT_IDS), 2)
    checkpoint = _load_checkpoint(source, total, chunk_size)
    if checkpoint["stage"] == "complete" and OUTPUT_PATH.exists():
        return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    tasks = [
        (index, chunk_size, total)
        for index in range(checkpoint["chunk_count"])
        if str(index) not in checkpoint["completed_chunks"]
    ]
    if max_chunks is not None:
        tasks = tasks[:max_chunks]
    if tasks:
        context = multiprocessing.get_context("fork")
        with context.Pool(processes=workers) as pool:
            for result in pool.imap_unordered(_process_chunk, tasks, chunksize=1):
                checkpoint["completed_chunks"][str(result["chunk_index"])] = result
                _write_json_atomic(CHECKPOINT_PATH, checkpoint)
                completed = len(checkpoint["completed_chunks"])
                if (
                    completed % 25 == 0
                    or completed == checkpoint["chunk_count"]
                    or result["unresolved"]
                ):
                    print(
                        f"chunks={completed}/{checkpoint['chunk_count']} "
                        f"last={result['chunk_index']} "
                        f"unresolved={len(result['unresolved'])}",
                        flush=True,
                    )
    if len(checkpoint["completed_chunks"]) < checkpoint["chunk_count"]:
        print(f"paused_checkpoint={CHECKPOINT_PATH}", flush=True)
        return None

    search = _aggregate(checkpoint)
    point_audit = json.loads(POINT_AUDIT_PATH.read_text(encoding="utf-8"))
    report = {
        "schema": "euclid-min-regular-257-all-point-line-chord-search/v1",
        "source": source,
        "semantics": {
            "removed_paid_drawables": ["BG0", "target_transfer"],
            "candidate_e_move": 68,
            "candidate_family": "one_line_through_two_distinct_available_points",
            "target_event": (
                "the_two_new_intersections_of_candidate_line_and_c0_are_adjacent"
            ),
            "strictness": (
                "每个否定结果均来自不含 0 的 128 位严格实球残差；区间未能排除的定义"
                "只记为未决，不会被误报为无解。"
            ),
            "limitations": [
                "本报告尚未检查新交点邻接已有目标圆点的直线事件。",
                "本报告尚未检查全部点定义的圆候选。",
            ],
        },
        "universe": {
            "available_points": len(_POINT_IDS),
            "exact_coordinate_points": point_audit["universe"][
                "materialized_exact_points"
            ],
            "strict_ball_residual_points": point_audit["universe"][
                "materialized_residual_points"
            ],
            "line_definitions": total,
        },
        "parallelization": {
            "workers": workers,
            "chunk_size": chunk_size,
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
    parser.add_argument("--chunk-size", type=int, default=1000)
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
    print(f"status={report['search']['status']}")


if __name__ == "__main__":
    main()
