"""并行搜索最大前沿全部 2103 个可用点定义的最后一个圆。"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import signal
from contextlib import contextmanager
from pathlib import Path

from final_pair_circle_search import (
    ball_circle_candidate_may_hit,
    ball_circle_carrier,
)
from run_68e_all_point_line_adjacent_search import _existing_carrier_balls
from run_68e_all_point_line_chord_search import (
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    POINT_AUDIT_PATH,
    ROOT,
    _base_sources,
    _load_point_cache,
    _write_json_atomic,
)


CHECKPOINT_PATH = ROOT / "tmp" / "m257-8-all-point-circle-parallel.json"
LOCK_PATH = ROOT / "tmp" / "m257-8-all-point-circle-parallel.lock"
OUTPUT_PATH = ROOT / "all-point-circle-search-68e.json"


_POINT_IDS: list[str] = []
_BALL_POINTS: list[tuple] = []
_BALL_EXISTING_CARRIERS: list[tuple] = []
_TARGET_CIRCLE_POINT_IDS: set[str] = set()


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
        "circle_module_sha256": _sha256_file(ROOT / "final_pair_circle_search.py"),
        "point_cache_helper_sha256": _sha256_file(
            ROOT / "run_68e_all_point_line_chord_search.py"
        ),
        "carrier_helper_sha256": _sha256_file(
            ROOT / "run_68e_all_point_line_adjacent_search.py"
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
            raise RuntimeError(f"已有全部点圆搜索在运行：PID {old_pid}")
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        break
    else:
        raise RuntimeError("无法取得全部点圆搜索锁")
    try:
        yield
    finally:
        try:
            owner = int(LOCK_PATH.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            owner = -1
        if owner == os.getpid():
            LOCK_PATH.unlink(missing_ok=True)


def _ordered_pair_at(index: int, point_count: int) -> tuple[int, int]:
    """返回所有 center != through 的字典序第 index 对。"""

    total = point_count * (point_count - 1)
    if index < 0 or index >= total:
        raise IndexError("有向点对索引越界")
    center = index // (point_count - 1)
    offset = index % (point_count - 1)
    through = offset if offset < center else offset + 1
    return center, through


def _available_target_circle_point_ids(point_ids: list[str]) -> set[str]:
    report = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    available = set(point_ids)
    result = {
        point["id"]
        for point in report["arrangement"]["points"]
        if point["id"] in available and "c0" in point["incident_drawables"]
    }
    if len(result) != 115:
        raise ValueError("最大前沿可用目标圆点数不再是 115")
    return result


def _process_chunk(task: tuple[int, int, int]) -> dict:
    chunk_index, chunk_size, total = task
    start = chunk_index * chunk_size
    end = min(start + chunk_size, total)
    point_count = len(_POINT_IDS)
    relation_checks = 0
    excluded = 0
    redrawn_target = []
    unresolved = []
    for definition_index in range(start, end):
        center_index, through_index = _ordered_pair_at(
            definition_index,
            point_count,
        )
        candidate = ball_circle_carrier(
            _BALL_POINTS[center_index],
            _BALL_POINTS[through_index],
        )
        may_hit, checks = ball_circle_candidate_may_hit(
            candidate,
            _BALL_EXISTING_CARRIERS,
        )
        relation_checks += checks
        if not may_hit:
            excluded += 1
            continue
        center_id = _POINT_IDS[center_index]
        through_id = _POINT_IDS[through_index]
        item = {
            "definition_index": definition_index,
            "center": center_id,
            "through": through_id,
        }
        if center_id == "C" and through_id in _TARGET_CIRCLE_POINT_IDS:
            redrawn_target.append(item)
        else:
            unresolved.append(item)
    return {
        "chunk_index": chunk_index,
        "definitions_tested": end - start,
        "ball_relation_checks": relation_checks,
        "ball_excluded_definitions": excluded,
        "redrawn_target_circle_definitions": redrawn_target,
        "unresolved": unresolved,
    }


def _load_checkpoint(source: dict, total: int, chunk_size: int) -> dict:
    chunk_count = (total + chunk_size - 1) // chunk_size
    if not CHECKPOINT_PATH.exists():
        return {
            "schema": "euclid-min-regular-257-all-point-circle-checkpoint/v1",
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
    redrawn = sorted(
        (
            item
            for chunk in ordered
            for item in chunk["redrawn_target_circle_definitions"]
        ),
        key=lambda item: item["definition_index"],
    )
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
        "redrawn_target_circle_definitions": redrawn,
        "redrawn_target_circle_count": len(redrawn),
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
    global _BALL_EXISTING_CARRIERS, _TARGET_CIRCLE_POINT_IDS
    _POINT_IDS, _BALL_POINTS = _load_point_cache()
    _BALL_EXISTING_CARRIERS = _existing_carrier_balls()
    _TARGET_CIRCLE_POINT_IDS = _available_target_circle_point_ids(_POINT_IDS)
    source = _sources()
    total = len(_POINT_IDS) * (len(_POINT_IDS) - 1)
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
                interesting = (
                    result["redrawn_target_circle_definitions"]
                    or result["unresolved"]
                )
                if (
                    completed % 25 == 0
                    or completed == checkpoint["chunk_count"]
                    or interesting
                ):
                    print(
                        f"chunks={completed}/{checkpoint['chunk_count']} "
                        f"last={result['chunk_index']} "
                        f"redraws={len(result['redrawn_target_circle_definitions'])} "
                        f"unresolved={len(result['unresolved'])}",
                        flush=True,
                    )
    if len(checkpoint["completed_chunks"]) < checkpoint["chunk_count"]:
        print(f"paused_checkpoint={CHECKPOINT_PATH}", flush=True)
        return None

    search = _aggregate(checkpoint)
    point_audit = json.loads(POINT_AUDIT_PATH.read_text(encoding="utf-8"))
    report = {
        "schema": "euclid-min-regular-257-all-point-circle-search/v1",
        "source": source,
        "semantics": {
            "removed_paid_drawables": ["BG0", "target_transfer"],
            "candidate_e_move": 68,
            "candidate_family": (
                "one_circle_with_distinct_available_center_and_through_point"
            ),
            "target_events": [
                "the_two_new_intersections_of_candidate_circle_and_c0_are_adjacent",
                "a_new_candidate_intersection_on_c0_is_adjacent_to_an_"
                "already_available_point_on_c0",
            ],
            "strictness": (
                "严格实球未能排除的定义只在能由关联表证明重画 c0 时判为无新交点；"
                "其余一律保留为未决。"
            ),
            "limitations": [
                "结论只覆盖删除第 68、69 步的最大前沿。",
                "结论只允许加入一个作为最后第 68E 的新对象。",
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
            "available_target_circle_points": len(_TARGET_CIRCLE_POINT_IDS),
            "existing_target_carriers": len(_BALL_EXISTING_CARRIERS),
            "circle_definitions": total,
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
