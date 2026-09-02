"""可暂停恢复地穷尽 M257-8 最后一步目标弦直线定义。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path

from final_pair_line_chord_search import (
    BALL_PRECISION,
    ball_line_chord_may_hit,
    deserialize_ball_point,
    exact_line_chord_hit,
    prepare_final_pair_line_universe,
    real_ball_point,
    serialize_ball_point,
)


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
FRONTIER_PATH = ROOT / "full-point-candidate-frontier-69e.json"
CACHE_PATH = ROOT / "tmp" / "m257-8-final-pair-point-balls.json"
CHECKPOINT_PATH = ROOT / "tmp" / "m257-8-final-pair-line-chord.json"
LOCK_PATH = ROOT / "tmp" / "m257-8-final-pair-line-chord.lock"
OUTPUT_PATH = ROOT / "final-pair-line-chord-search-68e.json"


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


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


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
            except (OSError, ValueError):
                old_pid = -1
            if _pid_is_alive(old_pid):
                raise RuntimeError(f"已有直线目标弦搜索在运行：PID {old_pid}")
            LOCK_PATH.unlink(missing_ok=True)
            continue
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        break
    else:
        raise RuntimeError("无法取得 M257-8 搜索锁")
    try:
        yield
    finally:
        try:
            owner = int(LOCK_PATH.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            owner = -1
        if owner == os.getpid():
            LOCK_PATH.unlink(missing_ok=True)


def _load_ball_cache(source: dict, point_ids: list[str]) -> dict:
    if not CACHE_PATH.exists():
        return {
            "schema": "euclid-min-regular-257-point-ball-cache/v1",
            "source": source,
            "precision_bits": BALL_PRECISION,
            "point_ids": point_ids,
            "next_point_index": 0,
            "balls": [],
        }
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if cache["source"] != source or cache["point_ids"] != point_ids:
        raise ValueError("严格实球缓存与当前输入不一致")
    if cache["precision_bits"] != BALL_PRECISION:
        raise ValueError("严格实球缓存精度不一致")
    return cache


def _complete_ball_cache(source: dict, point_items: list[tuple]) -> list[tuple]:
    point_ids = [name for name, _point in point_items]
    cache = _load_ball_cache(source, point_ids)
    for index in range(cache["next_point_index"], len(point_items)):
        name, point = point_items[index]
        cache["balls"].append(serialize_ball_point(real_ball_point(point)))
        cache["next_point_index"] = index + 1
        if cache["next_point_index"] % 10 == 0:
            _write_json_atomic(CACHE_PATH, cache)
            print(
                f"point_balls={cache['next_point_index']}/{len(point_items)} "
                f"last={name}",
                flush=True,
            )
    _write_json_atomic(CACHE_PATH, cache)
    return [deserialize_ball_point(value) for value in cache["balls"]]


def _load_checkpoint(source: dict, total: int) -> dict:
    if not CHECKPOINT_PATH.exists():
        return {
            "schema": "euclid-min-regular-257-final-pair-line-chord-checkpoint/v1",
            "source": source,
            "algorithm": _algorithm(),
            "total_definitions": total,
            "next_definition_index": 0,
            "ball_excluded_definitions": 0,
            "exact_checks": 0,
            "solutions": [],
            "stage": "definitions",
        }
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    if checkpoint["source"] != source:
        raise ValueError("搜索检查点输入摘要不一致")
    if checkpoint["algorithm"] != _algorithm():
        raise ValueError("搜索检查点由不同版本算法生成")
    if checkpoint["total_definitions"] != total:
        raise ValueError("搜索检查点定义总数不一致")
    return checkpoint


def run(*, chunk_size: int, max_chunks: int | None) -> dict | None:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    full_report = json.loads(FULL_CLOSURE_PATH.read_text(encoding="utf-8"))
    frontier = json.loads(FRONTIER_PATH.read_text(encoding="utf-8"))
    source = _sources()
    universe = prepare_final_pair_line_universe(
        certificate,
        frontier,
        trace=lambda message: print(message, flush=True),
    )
    point_items = universe["point_items"]
    ball_points = _complete_ball_cache(source, point_items)
    checkpoint = _load_checkpoint(source, universe["line_definitions"])
    if checkpoint["stage"] == "complete" and OUTPUT_PATH.exists():
        return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    chunks_completed = 0
    processed_in_chunk = 0
    next_index = checkpoint["next_definition_index"]
    for definition_index, (first_index, second_index) in enumerate(
        combinations(range(len(point_items)), 2)
    ):
        if definition_index < next_index:
            continue
        if ball_line_chord_may_hit(
            ball_points[first_index],
            ball_points[second_index],
        ):
            checkpoint["exact_checks"] += 1
            if exact_line_chord_hit(
                point_items[first_index][1],
                point_items[second_index][1],
            ):
                checkpoint["solutions"].append(
                    {
                        "definition_index": definition_index,
                        "through": [
                            point_items[first_index][0],
                            point_items[second_index][0],
                        ],
                    }
                )
        else:
            checkpoint["ball_excluded_definitions"] += 1
        checkpoint["next_definition_index"] = definition_index + 1
        processed_in_chunk += 1
        if processed_in_chunk >= chunk_size:
            _write_json_atomic(CHECKPOINT_PATH, checkpoint)
            chunks_completed += 1
            processed_in_chunk = 0
            print(
                f"line_definitions={checkpoint['next_definition_index']}/"
                f"{checkpoint['total_definitions']} "
                f"exact_checks={checkpoint['exact_checks']} "
                f"solutions={len(checkpoint['solutions'])}",
                flush=True,
            )
            if max_chunks is not None and chunks_completed >= max_chunks:
                print(f"paused_checkpoint={CHECKPOINT_PATH}", flush=True)
                return None
    _write_json_atomic(CHECKPOINT_PATH, checkpoint)
    report = {
        "schema": "euclid-min-regular-257-final-pair-line-chord-search/v1",
        "source": source,
        "semantics": {
            "removed_paid_drawables": universe["removed"],
            "selected_paid_drawables": universe["selected_paid_drawables"],
            "candidate_e_move": 68,
            "candidate_family": (
                "one_line_through_two_available_materialized_exact_points"
            ),
            "target_event": (
                "the_two_new_intersections_of_candidate_line_and_c0_are_adjacent"
            ),
            "limitations": [
                "尚未检查候选直线产生的新点与既有目标圆点相邻的情形。",
                "尚未检查候选圆，也未物化 474 个抽象残余圆交点。",
            ],
        },
        "universe": {
            "available_points": universe["available_points"],
            "available_exact_coordinate_points": len(point_items),
            "line_definitions": universe["line_definitions"],
        },
        "search": {
            "definitions_tested": checkpoint["next_definition_index"],
            "ball_excluded_definitions": checkpoint[
                "ball_excluded_definitions"
            ],
            "exact_checks": checkpoint["exact_checks"],
            "solutions": checkpoint["solutions"],
            "solutions_found": len(checkpoint["solutions"]),
            "status": (
                "solution_found"
                if checkpoint["solutions"]
                else "exhausted_no_solution"
            ),
        },
    }
    _write_json_atomic(OUTPUT_PATH, report)
    checkpoint["stage"] = "complete"
    checkpoint["output"] = OUTPUT_PATH.name
    _write_json_atomic(CHECKPOINT_PATH, checkpoint)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--max-chunks", type=int)
    args = parser.parse_args()
    if args.chunk_size <= 0:
        raise ValueError("chunk-size 必须为正数")

    def interrupt(_signal_number, _frame) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        with _single_runner():
            report = run(
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
