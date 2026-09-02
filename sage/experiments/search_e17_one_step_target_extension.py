"""穷尽固定 17E 前缀的全部一笔目标扩展，并按分片原子保存进度。"""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from time import perf_counter

from sage.version import version as sage_version

from euclid_min.canonical_json import sha256_hex
from euclid_min.geometry import Circle, Line, Point
from euclid_min.geometry_algebra_ir import replay_full_closure
from euclid_min.intersections import IntersectionKind, intersect
from euclid_min.replay import ProgramReplayer
from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import node_from_steps, steps_from_program
from euclid_min.search.sharded_checkpoint import (
    load_or_create_checkpoint,
    record_completed_shard,
    remaining_shard_ids,
    set_checkpoint_status,
)
from euclid_min.target import adjacent_targets
from euclid_min.verifier import verify_files
from experiments.build_detemple_1991_improved import DEFAULT_PROFILE
from experiments.build_regular17_geometry_algebra_ir import (
    CERTIFICATE_PATH,
    OUTPUT_PATH as GA_IR_PATH,
    REPOSITORY_ROOT,
)


DEFAULT_CHECKPOINT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e17-one-step-target-extension-checkpoint-sage-10.7.json"
)
DEFAULT_SUMMARY = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e17-one-step-target-extension-sage-10.7.json"
)
DEFAULT_CANDIDATE = (
    REPOSITORY_ROOT / "candidates" / "regular-17-18e-fixed-e17-extension.json"
)
SEARCH_SCRIPT_PATH = Path(__file__).resolve()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _program_prefix(program: list[dict], e_move: int) -> list[dict]:
    """保留指定 E 步及其后的零成本绑定，遇到下一笔绘制时停止。"""

    prefix = []
    paid = 0
    for entry in program:
        if entry["op"] in {"line", "circle"}:
            if paid >= e_move:
                break
            paid += 1
        prefix.append(entry)
    if paid != e_move:
        raise ValueError(f"程序不足 {e_move} E")
    return prefix


def _parameterizations(point_count: int) -> list[tuple[str, int, int]]:
    result = [
        ("line", first, second)
        for first in range(point_count)
        for second in range(first + 1, point_count)
    ]
    result.extend(
        ("circle", center, through)
        for center in range(point_count)
        for through in range(point_count)
        if center != through
    )
    return result


def _line_contains(first: Point, second: Point, target: Point) -> bool:
    return (
        (second.x - first.x) * (target.y - first.y)
        - (second.y - first.y) * (target.x - first.x)
        == 0
    )


def _circle_contains(center: Point, through: Point, target: Point) -> bool:
    through_dx = through.x - center.x
    through_dy = through.y - center.y
    target_dx = target.x - center.x
    target_dy = target.y - center.y
    return (
        through_dx * through_dx + through_dy * through_dy
        == target_dx * target_dx + target_dy * target_dy
    )


def _search_shard(
    state,
    points: tuple[Point, ...],
    parameterizations: list[tuple[str, int, int]],
    start: int,
    stop: int,
) -> dict:
    targets = adjacent_targets()
    hits = []
    line_count = 0
    circle_count = 0
    incident_parameterizations = 0
    existing_object_parameterizations = 0
    for parameter_index in range(start, stop):
        operation, first_index, second_index = parameterizations[parameter_index]
        first = points[first_index]
        second = points[second_index]
        if operation == "line":
            line_count += 1
            matched_targets = [
                name.value
                for name, target in targets.items()
                if _line_contains(first, second, target)
            ]
            if not matched_targets:
                continue
            incident_parameterizations += 1
            drawable = Line.through(first, second)
            if state.contains_line(drawable):
                existing_object_parameterizations += 1
                continue
        else:
            circle_count += 1
            matched_targets = [
                name.value
                for name, target in targets.items()
                if _circle_contains(first, second, target)
            ]
            if not matched_targets:
                continue
            incident_parameterizations += 1
            drawable = Circle.through(first, second)
            if state.contains_circle(drawable):
                existing_object_parameterizations += 1
                continue
        hits.append(
            {
                "parameter_index": parameter_index,
                "operation": operation,
                "first_point_index": first_index,
                "second_point_index": second_index,
                "targets": matched_targets,
            }
        )
    return {
        "range": [start, stop],
        "tested": stop - start,
        "line_parameterizations": line_count,
        "circle_parameterizations": circle_count,
        "target_incident_parameterizations": incident_parameterizations,
        "existing_object_parameterizations": existing_object_parameterizations,
        "new_target_hits": hits,
    }


def _point_reference(
    full,
    point: Point,
    *,
    generated_id: str,
) -> tuple[str, dict | None]:
    record = next(item for item in full.points if item.point == point)
    if record.aliases:
        return record.aliases[0], None
    drawable_by_id = {
        item.drawable_id: item.drawable for item in full.drawables
    }
    for first_id, second_id in combinations(record.incident_drawables, 2):
        result = intersect(drawable_by_id[first_id], drawable_by_id[second_id])
        if result.kind == IntersectionKind.COINCIDENT:
            continue
        for index, candidate in enumerate(result.points):
            if candidate == point:
                return generated_id, {
                    "id": generated_id,
                    "op": "intersect",
                    "objects": [first_id, second_id],
                    "index": index,
                }
    raise ValueError(f"无法为闭包点 {record.point_id} 选择确定性父对象")


def _candidate_drawable(
    points: tuple[Point, ...], hit: dict
):
    first = points[hit["first_point_index"]]
    second = points[hit["second_point_index"]]
    if hit["operation"] == "line":
        return Line.through(first, second)
    return Circle.through(first, second)


def _unique_hits(state, points: tuple[Point, ...], hits: list[dict]) -> list[dict]:
    unique: list[tuple[object, dict]] = []
    for hit in hits:
        drawable = _candidate_drawable(points, hit)
        if isinstance(drawable, Line) and state.contains_line(drawable):
            continue
        if isinstance(drawable, Circle) and state.contains_circle(drawable):
            continue
        existing = next(
            (
                record
                for old, record in unique
                if type(old) is type(drawable) and old == drawable
            ),
            None,
        )
        if existing is None:
            unique.append((drawable, {**hit, "equivalent_parameterizations": 1}))
        else:
            existing["equivalent_parameterizations"] += 1
            existing["targets"] = sorted(set(existing["targets"] + hit["targets"]))
    return [record for _drawable, record in unique]


def _build_candidate_certificate(
    certificate: dict,
    prefix_program: list[dict],
    points: tuple[Point, ...],
    hit: dict,
) -> dict:
    full = replay_full_closure(prefix_program)
    first = points[hit["first_point_index"]]
    second = points[hit["second_point_index"]]
    first_reference, first_binding = _point_reference(
        full, first, generated_id="ir_direct_input_1"
    )
    second_reference, second_binding = _point_reference(
        full, second, generated_id="ir_direct_input_2"
    )
    program = list(prefix_program)
    for binding in (first_binding, second_binding):
        if binding is not None:
            program.append(binding)
    if hit["operation"] == "line":
        program.append(
            {
                "id": "ir_direct_target_object",
                "op": "line",
                "through": [first_reference, second_reference],
            }
        )
    else:
        program.append(
            {
                "id": "ir_direct_target_object",
                "op": "circle",
                "center": first_reference,
                "through": second_reference,
            }
        )
    replay = ProgramReplayer().replay(program)
    if replay.e_move != 18 or not replay.targets:
        raise RuntimeError("一笔命中记录不能编译为有效 18E 程序")
    construction = {
        "id": "regular-17-18e-fixed-e17-extension",
        "title": "Regular 17-gon 18E fixed-prefix direct extension",
        "description": (
            "Exact one-draw extension discovered from the complete finite-real "
            "intersection closure of the verified 17E prefix."
        ),
        "program": program,
    }
    return {
        "schema": "euclid-min-certificate/v1",
        "problem": certificate["problem"],
        "profile": certificate["profile"],
        "construction": construction,
        "assertions": {
            "score": {"metric": "e_move", "e_move": 18},
            "targets": [target.value for target in replay.targets],
            "claim": "verified_construction",
        },
        "software": {
            "producer": {
                "name": "euclid-min-e17-one-step-target-extension",
                "version": "1",
            }
        },
        "integrity": {"construction_sha256": sha256_hex(construction)},
    }


def run(args) -> int:
    started = perf_counter()
    certificate = json.loads(args.certificate.read_text(encoding="utf-8"))
    program = certificate["construction"]["program"]
    prefix_program = _program_prefix(program, 17)
    node = node_from_steps(steps_from_program(prefix_program))
    if node.score != 17:
        raise ValueError("固定前缀没有精确重放为 17E")
    points = tuple(sorted(node.state.points))
    parameterizations = _parameterizations(len(points))
    shard_ranges = [
        (start, min(start + args.shard_size, len(parameterizations)))
        for start in range(0, len(parameterizations), args.shard_size)
    ]
    shard_ids = [f"{index:04d}" for index in range(len(shard_ranges))]
    input_sha256 = {
        str(args.certificate.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): _sha256_file(
            args.certificate
        ),
        str(args.ga_ir.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): _sha256_file(
            args.ga_ir
        ),
        str(SEARCH_SCRIPT_PATH.relative_to(REPOSITORY_ROOT)).replace(
            "\\", "/"
        ): _sha256_file(SEARCH_SCRIPT_PATH),
    }
    configuration = {
        "prefix_e_move": 17,
        "point_order": "exact_lexicographic_xy_ascending",
        "point_count": len(points),
        "parameterization_order": "all_unordered_lines_then_all_ordered_circles",
        "parameterization_count": len(parameterizations),
        "shard_size": args.shard_size,
        "targets": [target.value for target in adjacent_targets()],
        "acceptance": "exact_object_incidence_and_new_object_check",
        "reference_check": "full_exact_candidate_generation_then_object_contains",
    }
    checkpoint = load_or_create_checkpoint(
        args.checkpoint,
        task_id="regular-17-e17-one-step-target-extension-v1",
        profile_path=args.profile,
        input_sha256=input_sha256,
        configuration=configuration,
        shard_ids=shard_ids,
    )
    if checkpoint["progress"]["status"] != "completed":
        checkpoint = set_checkpoint_status(args.checkpoint, checkpoint, "running")

    completed_this_run = 0
    try:
        remaining = remaining_shard_ids(checkpoint)
        for shard_id in remaining:
            shard_index = int(shard_id)
            start, stop = shard_ranges[shard_index]
            result = _search_shard(
                node.state,
                points,
                parameterizations,
                start,
                stop,
            )
            checkpoint = record_completed_shard(
                args.checkpoint,
                checkpoint,
                shard_id=shard_id,
                result=result,
            )
            completed_this_run += 1
            print(
                json.dumps(
                    {
                        "event": "shard_complete",
                        "shard": shard_id,
                        "completed": len(
                            checkpoint["progress"]["completed_shards"]
                        ),
                        "total": len(shard_ids),
                        "tested": result["tested"],
                        "new_target_hits": len(result["new_target_hits"]),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if (
                args.max_shards is not None
                and completed_this_run >= args.max_shards
                and remaining_shard_ids(checkpoint)
            ):
                checkpoint = set_checkpoint_status(
                    args.checkpoint, checkpoint, "paused"
                )
                print(
                    json.dumps(
                        {
                            "event": "paused",
                            "remaining_shards": len(
                                remaining_shard_ids(checkpoint)
                            ),
                            "checkpoint": str(args.checkpoint),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                return 3
    except KeyboardInterrupt:
        set_checkpoint_status(args.checkpoint, checkpoint, "paused")
        print(
            json.dumps(
                {
                    "event": "interrupted",
                    "checkpoint": str(args.checkpoint),
                    "remaining_shards": len(remaining_shard_ids(checkpoint)),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return 130

    checkpoint = set_checkpoint_status(args.checkpoint, checkpoint, "completed")
    shard_results = [
        item["result"] for item in checkpoint["progress"]["completed_shards"]
    ]
    raw_hits = [
        hit for result in shard_results for hit in result["new_target_hits"]
    ]
    unique_hits = _unique_hits(node.state, points, raw_hits)
    reference_candidates = generate_candidates(node.state)
    reference_target_candidates = [
        candidate
        for candidate in reference_candidates
        if any(
            candidate.drawable().contains(target)
            for target in adjacent_targets().values()
        )
    ]
    if len(reference_target_candidates) != len(unique_hits):
        raise RuntimeError(
            "参数化入射扫描与完整候选生成的目标对象数量不一致"
        )
    certificate_valid = None
    candidate_path = None
    if unique_hits:
        candidate = _build_candidate_certificate(
            certificate,
            prefix_program,
            points,
            unique_hits[0],
        )
        args.candidate.parent.mkdir(parents=True, exist_ok=True)
        args.candidate.write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        certificate_valid = verify_files(args.candidate, args.profile).valid
        candidate_path = str(args.candidate.relative_to(REPOSITORY_ROOT)).replace(
            "\\", "/"
        )
        if not certificate_valid:
            raise RuntimeError("搜索命中生成的 18E 证书未通过独立 verifier")

    total_tested = sum(result["tested"] for result in shard_results)
    summary = {
        "schema": "euclid-min-fixed-prefix-one-step-search/v1",
        "mode": "exact_fixed_prefix_exhaustive",
        "source": {
            "certificate_sha256": input_sha256[
                str(args.certificate.relative_to(REPOSITORY_ROOT)).replace(
                    "\\", "/"
                )
            ],
            "geometry_algebra_ir_sha256": input_sha256[
                str(args.ga_ir.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
            ],
        },
        "scope": {
            "prefix_e_move": 17,
            "extension_budget_e": 1,
            "prefix_points": len(points),
            "prefix_lines": len(node.state.lines),
            "prefix_circles": len(node.state.circles),
            "targets": configuration["targets"],
        },
        "coverage": {
            "shards": len(shard_ids),
            "completed_shards": len(shard_results),
            "parameterizations": len(parameterizations),
            "tested_parameterizations": total_tested,
            "line_parameterizations": sum(
                result["line_parameterizations"] for result in shard_results
            ),
            "circle_parameterizations": sum(
                result["circle_parameterizations"] for result in shard_results
            ),
            "target_incident_parameterizations": sum(
                result["target_incident_parameterizations"]
                for result in shard_results
            ),
            "existing_object_parameterizations": sum(
                result["existing_object_parameterizations"]
                for result in shard_results
            ),
        },
        "result": {
            "raw_new_target_parameterizations": len(raw_hits),
            "unique_new_target_objects": len(unique_hits),
            "hits": unique_hits,
            "candidate_certificate": candidate_path,
            "candidate_certificate_valid": certificate_valid,
        },
        "checkpoint": {
            "schema": checkpoint["schema"],
            "task_signature": checkpoint["task"]["signature"],
            "revision": checkpoint["progress"]["revision"],
            "status": checkpoint["progress"]["status"],
        },
        "reference_replay": {
            "method": "full_exact_candidate_generation_then_object_contains",
            "unique_new_candidates": len(reference_candidates),
            "unique_new_target_objects": len(reference_target_candidates),
            "agrees_with_sharded_scan": True,
        },
        "environment": {"sage_version": sage_version},
        "elapsed_seconds_this_invocation": perf_counter() - started,
        "interpretation": (
            "该结果精确穷尽已验证 19E 路线固定前 17E 状态的所有一步合法扩展；"
            "零命中只排除把这个固定前缀直接延长为 18E，不排除其他 18E 前缀或"
            "全局 18E 构造。"
        ),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    # 完整零命中也是一次成功完成的有限搜索；若命中但证书无效，上面已经报错。
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--certificate", type=Path, default=CERTIFICATE_PATH)
    parser.add_argument("--ga-ir", type=Path, default=GA_IR_PATH)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--shard-size", type=int, default=256)
    parser.add_argument(
        "--max-shards",
        type=int,
        help="本次最多完成多少新分片；用于验证暂停与恢复。",
    )
    args = parser.parse_args()
    if args.shard_size < 1:
        parser.error("--shard-size 必须为正整数")
    if args.max_shards is not None and args.max_shards < 1:
        parser.error("--max-shards 必须为正整数")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
