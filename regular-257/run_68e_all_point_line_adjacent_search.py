"""并行搜索全部 2103 个可用点定义的直线是否邻接已有目标圆点。"""

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
    ball_candidate_may_reach_existing,
    ball_carrier,
    ball_line_carrier,
    carrier_has_real_target_point,
    target_carrier,
)
from semantic_dependency import exact_replay_universe
from run_68e_all_point_line_chord_search import (
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    POINT_AUDIT_PATH,
    ROOT,
    _base_sources,
    _load_point_cache,
    _pair_at,
    _write_json_atomic,
)


CHECKPOINT_PATH = ROOT / "tmp" / "m257-8-all-point-line-adjacent-parallel.json"
LOCK_PATH = ROOT / "tmp" / "m257-8-all-point-line-adjacent-parallel.lock"
OUTPUT_PATH = ROOT / "all-point-line-adjacent-search-68e.json"


_POINT_IDS: list[str] = []
_BALL_POINTS: list[tuple] = []
_BALL_EXISTING_CARRIERS: list[tuple] = []


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sources() -> dict:
    return {
        **_base_sources(),
        "residual_point_ball_audit": POINT_AUDIT_PATH.name,
        "residual_point_ball_audit_sha256": _sha256_file(POINT_AUDIT_PATH),
    }


def _algorithm() -> dict:
    return {
        "runner_sha256": _sha256_file(Path(__file__).resolve()),
        "adjacent_module_sha256": _sha256_file(
            ROOT / "final_pair_line_adjacent_search.py"
        ),
        "point_cache_helper_sha256": _sha256_file(
            ROOT / "run_68e_all_point_line_chord_search.py"
        ),
    }


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
            raise RuntimeError(f"已有全部点直线邻接搜索在运行：PID {old_pid}")
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        break
    else:
        raise RuntimeError("无法取得全部点直线邻接搜索锁")
    try:
        yield
    finally:
        try:
            owner = int(LOCK_PATH.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            owner = -1
        if owner == os.getpid():
            LOCK_PATH.unlink(missing_ok=True)


def _existing_carrier_balls() -> list[tuple]:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    replay = exact_replay_universe(certificate)
    drawable_values = dict(replay["drawable_items"])
    target_circle = drawable_values["c0"]
    removed = {"BG0", "target_transfer"}
    carriers = []
    for name, drawable in replay["drawable_items"]:
        if name == "c0" or name in removed:
            continue
        carrier = target_carrier(drawable, target_circle)
        if carrier is not None and carrier_has_real_target_point(carrier):
            carriers.append(ball_carrier(carrier))
    if len(carriers) != 67:
        raise ValueError("最大前沿的既有目标弦载线数量不再是 67")
    return carriers


def _process_chunk(task: tuple[int, int, int]) -> dict:
    chunk_index, chunk_size, total = task
    start = chunk_index * chunk_size
    end = min(start + chunk_size, total)
    point_count = len(_POINT_IDS)
    first_index, second_index = _pair_at(start, point_count)
    relation_checks = 0
    excluded = 0
    unresolved = []
    for definition_index in range(start, end):
        candidate = ball_line_carrier(
            _BALL_POINTS[first_index],
            _BALL_POINTS[second_index],
        )
        may_hit, checks = ball_candidate_may_reach_existing(
            candidate,
            _BALL_EXISTING_CARRIERS,
        )
        relation_checks += checks
        if may_hit:
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
        "ball_relation_checks": relation_checks,
        "ball_excluded_definitions": excluded,
        "unresolved": unresolved,
    }


def _load_checkpoint(source: dict, total: int, chunk_size: int) -> dict:
    chunk_count = (total + chunk_size - 1) // chunk_size
    if not CHECKPOINT_PATH.exists():
        return {
            "schema": "euclid-min-regular-257-all-point-line-adjacent-checkpoint/v1",
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
    global _POINT_IDS, _BALL_POINTS, _BALL_EXISTING_CARRIERS
    _POINT_IDS, _BALL_POINTS = _load_point_cache()
    _BALL_EXISTING_CARRIERS = _existing_carrier_balls()
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
        "schema": "euclid-min-regular-257-all-point-line-adjacent-search/v1",
        "source": source,
        "semantics": {
            "removed_paid_drawables": ["BG0", "target_transfer"],
            "candidate_e_move": 68,
            "candidate_family": "one_line_through_two_distinct_available_points",
            "target_event": (
                "a_new_candidate_intersection_on_c0_is_adjacent_to_an_"
                "already_available_point_on_c0"
            ),
            "strictness": (
                "区间未能排除的定义只记为未决；只有全部关系残差均由严格实球排除时，"
                "该定义才计入否定结果。"
            ),
            "limitations": [
                "需与全部点目标弦报告合并，才完整覆盖该分片的直线候选。",
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
            "existing_target_carriers": len(_BALL_EXISTING_CARRIERS),
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
