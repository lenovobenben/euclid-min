"""可暂停恢复地运行 M257-7 具名点单新对象替换搜索。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path

from named_new_object_search import (
    ball_may_be_collinear,
    collinear,
    enumerate_rich_candidates,
    real_ball_point,
    search_named_replacements,
)
from semantic_dependency import exact_replay_universe


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
SEMANTIC_PATH = ROOT / "semantic-dependencies-69e.json"
FULL_CLOSURE_PATH = ROOT / "full-intersection-closure-69e.json"
CHECKPOINT_PATH = ROOT / "tmp" / "m257-7-named-search-checkpoint.json"
LOCK_PATH = ROOT / "tmp" / "m257-7-named-search.lock"
OUTPUT_PATH = ROOT / "named-new-object-search-69e.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sources() -> dict:
    return {
        "certificate": CERTIFICATE_PATH.name,
        "certificate_sha256": _sha256_file(CERTIFICATE_PATH),
        "semantic_dependency_report": SEMANTIC_PATH.name,
        "semantic_dependency_report_sha256": _sha256_file(SEMANTIC_PATH),
        "full_intersection_closure_report": FULL_CLOSURE_PATH.name,
        "full_intersection_closure_report_sha256": _sha256_file(
            FULL_CLOSURE_PATH
        ),
    }


def _algorithm() -> dict:
    search_module = ROOT / "named_new_object_search.py"
    runner = Path(__file__).resolve()
    return {
        "runner_sha256": _sha256_file(runner),
        "search_module_sha256": _sha256_file(search_module),
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


def _new_checkpoint(source: dict, total_triples: int) -> dict:
    return {
        "schema": "euclid-min-regular-257-named-new-object-checkpoint/v3",
        "source": source,
        "algorithm": _algorithm(),
        "stage": "collinear_triples",
        "next_triple_index": 0,
        "total_triples": total_triples,
        "collinear_triples": [],
        "filter": {
            "kind": "rigorous_real_ball_determinant",
            "precision_bits": 128,
            "ball_excluded_triples": 0,
            "exact_collinearity_checks": 0,
        },
    }


def _load_checkpoint(source: dict, total_triples: int) -> dict:
    if not CHECKPOINT_PATH.exists():
        return _new_checkpoint(source, total_triples)
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    if checkpoint["source"] != source:
        raise ValueError(
            "检查点输入摘要已过期；请移走 regular-257/tmp/"
            "m257-7-named-search-checkpoint.json 后重新运行"
        )
    if checkpoint["total_triples"] != total_triples:
        raise ValueError("检查点三元组总数不一致")
    if "algorithm" in checkpoint and checkpoint["algorithm"] != _algorithm():
        raise ValueError("检查点由不同版本的搜索程序生成，不能自动续跑")
    # v1 在所有三元组上直接做精确判定；其结果可无损迁移到 v2，随后
    # 尚未扫描的三元组再使用严格实球区间预筛。
    if "filter" not in checkpoint:
        checkpoint["filter"] = {
            "kind": "rigorous_real_ball_determinant",
            "precision_bits": 128,
            "ball_excluded_triples": 0,
            "exact_collinearity_checks": checkpoint["next_triple_index"],
        }
    checkpoint["schema"] = (
        "euclid-min-regular-257-named-new-object-checkpoint/v3"
    )
    checkpoint["algorithm"] = _algorithm()
    return checkpoint


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


@contextmanager
def _single_runner():
    """阻止两个进程同时覆盖同一份检查点。"""

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
                raise RuntimeError(f"已有搜索进程正在运行：PID {old_pid}")
            LOCK_PATH.unlink(missing_ok=True)
            continue
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{os.getpid()}\n")
        break
    else:
        raise RuntimeError("无法取得 M257-7 搜索锁")
    try:
        yield
    finally:
        try:
            owner = int(LOCK_PATH.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            owner = -1
        if owner == os.getpid():
            LOCK_PATH.unlink(missing_ok=True)


def run(*, chunk_size: int, max_chunks: int | None) -> dict | None:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    semantic_report = json.loads(SEMANTIC_PATH.read_text(encoding="utf-8"))
    source = _sources()
    replay = exact_replay_universe(certificate)
    point_values = [point for _name, point in replay["point_items"]]
    ball_points = [real_ball_point(point) for point in point_values]
    triples = combinations(range(len(point_values)), 3)
    total_triples = len(point_values) * (len(point_values) - 1) * (
        len(point_values) - 2
    ) // 6
    checkpoint = _load_checkpoint(source, total_triples)
    if checkpoint["stage"] == "complete" and OUTPUT_PATH.exists():
        report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if report["source"] == source:
            return report
    next_index = checkpoint["next_triple_index"]
    chunks_completed = 0
    processed_in_chunk = 0
    if checkpoint["stage"] == "collinear_triples":
        for triple_index, triple in enumerate(triples):
            if triple_index < next_index:
                continue
            first, second, third = triple
            if ball_may_be_collinear(
                ball_points[first],
                ball_points[second],
                ball_points[third],
            ):
                checkpoint["filter"]["exact_collinearity_checks"] += 1
                if collinear(
                    point_values[first],
                    point_values[second],
                    point_values[third],
                ):
                    checkpoint["collinear_triples"].append(list(triple))
            else:
                checkpoint["filter"]["ball_excluded_triples"] += 1
            checkpoint["next_triple_index"] = triple_index + 1
            processed_in_chunk += 1
            if processed_in_chunk >= chunk_size:
                _write_json_atomic(CHECKPOINT_PATH, checkpoint)
                chunks_completed += 1
                processed_in_chunk = 0
                print(
                    f"collinear_triples={checkpoint['next_triple_index']}/"
                    f"{total_triples} hits={len(checkpoint['collinear_triples'])}",
                    flush=True,
                )
                if max_chunks is not None and chunks_completed >= max_chunks:
                    print(f"paused_checkpoint={CHECKPOINT_PATH}")
                    return None
        _write_json_atomic(CHECKPOINT_PATH, checkpoint)
        checkpoint["stage"] = "candidate_enumeration"
        _write_json_atomic(CHECKPOINT_PATH, checkpoint)

    if checkpoint["stage"] == "candidate_enumeration":
        print("candidate_enumeration=started", flush=True)
        candidates, enumeration = enumerate_rich_candidates(
            certificate,
            checkpoint["collinear_triples"],
            ball_points=ball_points,
        )
        checkpoint["candidates"] = candidates
        checkpoint["enumeration"] = enumeration
        checkpoint["search_state"] = None
        checkpoint["stage"] = "replacement_search"
        _write_json_atomic(CHECKPOINT_PATH, checkpoint)
        print(
            f"candidate_enumeration=complete candidates={len(candidates)}",
            flush=True,
        )
    else:
        candidates = checkpoint["candidates"]
        enumeration = checkpoint["enumeration"]

    def save_search_state(state: dict) -> None:
        checkpoint["search_state"] = state
        _write_json_atomic(CHECKPOINT_PATH, checkpoint)

    search = search_named_replacements(
        semantic_report,
        candidates,
        state=checkpoint.get("search_state"),
        progress=lambda message: print(message, flush=True),
        checkpoint=save_search_state,
    )
    report = {
        "schema": "euclid-min-regular-257-named-new-object-search-report/v1",
        "source": source,
        "semantics": {
            "point_universe": "the_83_named_points",
            "old_drawable_universe": "the_69_verified_paid_drawables",
            "new_drawables": "one_new_line_or_circle_defined_by_named_points",
            "candidate_pruning": (
                "只保留经过额外具名点的新对象；只经过定义点的对象不能在具名点"
                "闭包中产生新点。"
            ),
            "limitations": [
                "新对象与旧对象产生的未命名交点尚未纳入本轮搜索。",
                "本轮只加入一个新对象；结论不是所有 68E 构造的不存在性证明。",
            ],
        },
        "enumeration": enumeration,
        "collinearity_filter": checkpoint["filter"],
        "candidates": candidates,
        "search": search,
        "conclusion": (
            "若结果为空，则在具名点定义的单新对象候选宇宙内，不存在删除至少"
            "两个旧对象而取得净降步的方案。"
        ),
    }
    _write_json_atomic(OUTPUT_PATH, report)
    checkpoint["stage"] = "complete"
    checkpoint["output"] = OUTPUT_PATH.name
    _write_json_atomic(CHECKPOINT_PATH, checkpoint)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=2500)
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
            report = run(chunk_size=args.chunk_size, max_chunks=args.max_chunks)
    except KeyboardInterrupt:
        print(f"interrupted_checkpoint={CHECKPOINT_PATH}", flush=True)
        return
    if report is None:
        return
    print(f"wrote={OUTPUT_PATH}")
    print(
        f"candidates={report['search']['candidate_count']} "
        f"closure_trials={report['search']['closure_trials']}"
    )
    print(f"solutions_found={report['search']['solutions_found']}")


if __name__ == "__main__":
    main()
