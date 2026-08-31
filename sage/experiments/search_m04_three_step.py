"""从 E12 搜索至多三步得到 M0_4，并在命中后接回已知三步尾部。"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import multiprocessing
import os
from pathlib import Path
import sys
from time import perf_counter

from euclid_min.geometry import Circle, Line, Point
from euclid_min.search import Candidate, PointGoal
from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import (
    build_certificate_from_steps,
    steps_from_program,
)
from euclid_min.search.heuristic import TargetCandidateHeuristic
from euclid_min.search.model import SearchNode
from euclid_min.verifier import verify_files
from experiments.build_detemple_1991_improved import (
    DEFAULT_PROFILE,
    build_program,
)
from experiments.search_detemple_suffix import exact_prefix


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "candidates" / "regular-17-18e-m04.json"
DEFAULT_SUMMARY_OUTPUT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e12-m04-three-step-search-sage-10.7.json"
)
_ROUND_DIGITS = 11
_RESIDUAL_THRESHOLD = 1e-10


@dataclass(frozen=True, slots=True)
class NumericFirstStep:
    index: int
    candidate: Candidate
    first_residual: float
    second_residual: float
    new_numeric_points: int


def _target_and_tail():
    steps = steps_from_program(build_program())
    target = steps[16].first
    return target, steps[16:19]


def _line_float(line: Line):
    return ("line", float(line.a), float(line.b), float(line.c))


def _circle_float(circle: Circle):
    return (
        "circle",
        float(circle.center.x),
        float(circle.center.y),
        float(circle.radius_squared),
    )


def _drawable_float(drawable):
    return (
        _line_float(drawable)
        if isinstance(drawable, Line)
        else _circle_float(drawable)
    )


def _point_key(point: tuple[float, float]):
    return (round(point[0], _ROUND_DIGITS), round(point[1], _ROUND_DIGITS))


def _line_key(first, second):
    x1, y1 = first
    x2, y2 = second
    a = y1 - y2
    b = x2 - x1
    c = x1 * y2 - x2 * y1
    if a == 0.0 and b == 0.0:
        return None
    scale = a if a != 0.0 else b
    return (
        "line",
        round(a / scale, _ROUND_DIGITS),
        round(b / scale, _ROUND_DIGITS),
        round(c / scale, _ROUND_DIGITS),
    )


def _circle_key(center, through):
    cx, cy = center
    tx, ty = through
    radius_squared = (tx - cx) ** 2 + (ty - cy) ** 2
    return (
        "circle",
        round(cx, _ROUND_DIGITS),
        round(cy, _ROUND_DIGITS),
        round(radius_squared, _ROUND_DIGITS),
    )


def _drawable_key(drawable):
    if drawable[0] == "line":
        _kind, a, b, c = drawable
        scale = a if a != 0.0 else b
        return (
            "line",
            round(a / scale, _ROUND_DIGITS),
            round(b / scale, _ROUND_DIGITS),
            round(c / scale, _ROUND_DIGITS),
        )
    _kind, cx, cy, radius_squared = drawable
    return (
        "circle",
        round(cx, _ROUND_DIGITS),
        round(cy, _ROUND_DIGITS),
        round(radius_squared, _ROUND_DIGITS),
    )


def _line_line(first, second):
    _, a1, b1, c1 = first
    _, a2, b2, c2 = second
    determinant = a1 * b2 - a2 * b1
    if abs(determinant) < 1e-14:
        return ()
    return (
        (
            (b1 * c2 - b2 * c1) / determinant,
            (c1 * a2 - c2 * a1) / determinant,
        ),
    )


def _line_circle(line, circle):
    _, a, b, c = line
    _, center_x, center_y, radius_squared = circle
    denominator = a * a + b * b
    if denominator == 0.0:
        return ()
    scale = (a * center_x + b * center_y + c) / denominator
    foot_x = center_x - a * scale
    foot_y = center_y - b * scale
    distance_squared = (foot_x - center_x) ** 2 + (foot_y - center_y) ** 2
    height_squared = radius_squared - distance_squared
    tolerance = 1e-12 * max(1.0, abs(radius_squared))
    if height_squared < -tolerance:
        return ()
    if height_squared <= tolerance:
        return ((foot_x, foot_y),)
    offset = math.sqrt(height_squared / denominator)
    return (
        (foot_x - b * offset, foot_y + a * offset),
        (foot_x + b * offset, foot_y - a * offset),
    )


def _circle_circle(first, second):
    _, x1, y1, r1_squared = first
    _, x2, y2, r2_squared = second
    dx = x2 - x1
    dy = y2 - y1
    distance_squared = dx * dx + dy * dy
    if distance_squared == 0.0:
        return ()
    distance = math.sqrt(distance_squared)
    r1 = math.sqrt(max(0.0, r1_squared))
    r2 = math.sqrt(max(0.0, r2_squared))
    tolerance = 1e-12 * max(1.0, r1, r2, distance)
    if distance > r1 + r2 + tolerance:
        return ()
    if distance < abs(r1 - r2) - tolerance:
        return ()
    along = (r1_squared - r2_squared + distance_squared) / (2 * distance)
    height_squared = r1_squared - along * along
    if height_squared < -tolerance:
        return ()
    base_x = x1 + along * dx / distance
    base_y = y1 + along * dy / distance
    if height_squared <= tolerance:
        return ((base_x, base_y),)
    height = math.sqrt(height_squared)
    offset_x = -dy * height / distance
    offset_y = dx * height / distance
    return (
        (base_x + offset_x, base_y + offset_y),
        (base_x - offset_x, base_y - offset_y),
    )


def _numeric_intersections(first, second):
    if first[0] == "line" and second[0] == "line":
        return _line_line(first, second)
    if first[0] == "line" and second[0] == "circle":
        return _line_circle(first, second)
    if first[0] == "circle" and second[0] == "line":
        return _line_circle(second, first)
    return _circle_circle(first, second)


def _line_residual(first, second, target):
    x1, y1 = first
    x2, y2 = second
    target_x, target_y = target
    dx = x2 - x1
    dy = y2 - y1
    denominator = math.hypot(dx, dy)
    if denominator == 0.0:
        return math.inf
    return abs(dx * (target_y - y1) - dy * (target_x - x1)) / denominator


def _circle_residual(center, through, target):
    center_x, center_y = center
    through_x, through_y = through
    target_x, target_y = target
    radius_squared = (
        (through_x - center_x) ** 2 + (through_y - center_y) ** 2
    )
    return abs(
        (target_x - center_x) ** 2
        + (target_y - center_y) ** 2
        - radius_squared
    ) / max(1.0, abs(radius_squared))


_NUMERIC_POINTS = ()
_NUMERIC_POINT_KEYS = set()
_NUMERIC_EXISTING_DRAWABLES = ()
_NUMERIC_EXISTING_KEYS = set()
_NUMERIC_TARGET = (0.0, 0.0)
_NUMERIC_CANDIDATES = ()


def _numeric_score_index(index):
    candidate = _NUMERIC_CANDIDATES[index]
    candidate_drawable = _drawable_float(candidate.drawable())
    new_points = []
    seen_points = set(_NUMERIC_POINT_KEYS)
    for existing in _NUMERIC_EXISTING_DRAWABLES:
        for point in _numeric_intersections(candidate_drawable, existing):
            if not all(math.isfinite(coordinate) for coordinate in point):
                continue
            key = _point_key(point)
            if key in seen_points:
                continue
            seen_points.add(key)
            new_points.append(point)

    residual_by_key = {}
    candidate_key = _drawable_key(candidate_drawable)
    if candidate_drawable[0] == "line":
        _, a, b, c = candidate_drawable
        residual_by_key[candidate_key] = abs(
            a * _NUMERIC_TARGET[0] + b * _NUMERIC_TARGET[1] + c
        ) / math.hypot(a, b)
    else:
        _, cx, cy, radius_squared = candidate_drawable
        residual_by_key[candidate_key] = abs(
            (_NUMERIC_TARGET[0] - cx) ** 2
            + (_NUMERIC_TARGET[1] - cy) ** 2
            - radius_squared
        ) / max(1.0, abs(radius_squared))

    expanded_points = (*_NUMERIC_POINTS, *new_points)
    new_point_keys = {_point_key(point) for point in new_points}
    for first_index, first in enumerate(expanded_points):
        first_is_new = _point_key(first) in new_point_keys
        for second in expanded_points[first_index + 1 :]:
            if not (first_is_new or _point_key(second) in new_point_keys):
                continue
            key = _line_key(first, second)
            if (
                key is None
                or key in _NUMERIC_EXISTING_KEYS
                or key == candidate_key
            ):
                continue
            residual = _line_residual(first, second, _NUMERIC_TARGET)
            residual_by_key[key] = min(
                residual_by_key.get(key, math.inf), residual
            )
    for center in expanded_points:
        center_is_new = _point_key(center) in new_point_keys
        for through in expanded_points:
            if _point_key(center) == _point_key(through):
                continue
            if not (center_is_new or _point_key(through) in new_point_keys):
                continue
            key = _circle_key(center, through)
            if key in _NUMERIC_EXISTING_KEYS or key == candidate_key:
                continue
            residual = _circle_residual(center, through, _NUMERIC_TARGET)
            residual_by_key[key] = min(
                residual_by_key.get(key, math.inf), residual
            )
    residuals = sorted(residual_by_key.values())
    return NumericFirstStep(
        index=index,
        candidate=candidate,
        first_residual=residuals[0] if residuals else math.inf,
        second_residual=residuals[1] if len(residuals) > 1 else math.inf,
        new_numeric_points=len(new_points),
    )


def _numeric_first_step_scores(node: SearchNode, target: Point, workers: int):
    global _NUMERIC_POINTS
    global _NUMERIC_POINT_KEYS
    global _NUMERIC_EXISTING_DRAWABLES
    global _NUMERIC_EXISTING_KEYS
    global _NUMERIC_TARGET
    global _NUMERIC_CANDIDATES
    _NUMERIC_POINTS = tuple(
        (float(point.x), float(point.y)) for point in node.state.points
    )
    _NUMERIC_POINT_KEYS = {_point_key(point) for point in _NUMERIC_POINTS}
    _NUMERIC_EXISTING_DRAWABLES = tuple(
        _drawable_float(drawable) for drawable in node.state.drawables
    )
    _NUMERIC_EXISTING_KEYS = {
        _drawable_key(drawable) for drawable in _NUMERIC_EXISTING_DRAWABLES
    }
    _NUMERIC_TARGET = (float(target.x), float(target.y))
    _NUMERIC_CANDIDATES = generate_candidates(node.state)
    context = multiprocessing.get_context("fork")
    with context.Pool(processes=workers) as pool:
        rows = pool.map(
            _numeric_score_index,
            range(len(_NUMERIC_CANDIDATES)),
            chunksize=8,
        )
    rows.sort(
        key=lambda row: (
            row.first_residual,
            row.second_residual,
            -row.new_numeric_points,
            row.index,
        )
    )
    return rows


def _exact_target_candidates(state, target: Point):
    heuristic = TargetCandidateHeuristic(target)
    heuristic.prepare_state(state)
    seen = []
    points = tuple(sorted(state.points))

    def consider(op, first, second):
        score = heuristic.evaluate_points(op, first, second)
        if score is None or score.incidence_residual > _RESIDUAL_THRESHOLD:
            return
        candidate = Candidate(op, first, second)
        drawable = candidate.drawable()
        if not drawable.contains(target):
            return
        if op == "line" and state.contains_line(drawable):
            return
        if op == "circle" and state.contains_circle(drawable):
            return
        if any(type(old) is type(drawable) and old == drawable for old, _ in seen):
            return
        seen.append((drawable, candidate))

    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            consider("line", first, second)
    for center in points:
        for through in points:
            if center != through:
                consider("circle", center, through)
    return tuple(candidate for _drawable, candidate in seen)


_WORKER_NODE = None
_WORKER_TARGET = None
_WORKER_MAX_LOCAL_STEPS = 3


def _initialize_worker(node, target, max_local_steps):
    global _WORKER_NODE, _WORKER_TARGET, _WORKER_MAX_LOCAL_STEPS
    _WORKER_NODE = node
    _WORKER_TARGET = target
    _WORKER_MAX_LOCAL_STEPS = max_local_steps


def _evaluate_first_step(indexed_candidate):
    index, candidate = indexed_candidate
    started_at = perf_counter()
    child = _WORKER_NODE.apply(candidate)
    goal = PointGoal(_WORKER_TARGET)
    if goal.reached(child.state):
        return index, (candidate,), perf_counter() - started_at, 0

    second_candidates = _exact_target_candidates(child.state, _WORKER_TARGET)
    exact_candidates_tested = len(second_candidates)
    for second in second_candidates:
        grandchild = child.apply(second)
        if goal.reached(grandchild.state):
            return (
                index,
                (candidate, second),
                perf_counter() - started_at,
                exact_candidates_tested,
            )
        if _WORKER_MAX_LOCAL_STEPS < 3:
            continue
        third_candidates = _exact_target_candidates(
            grandchild.state,
            _WORKER_TARGET,
        )
        exact_candidates_tested += len(third_candidates)
        if third_candidates:
            return (
                index,
                (candidate, second, third_candidates[0]),
                perf_counter() - started_at,
                exact_candidates_tested,
            )
    return index, None, perf_counter() - started_at, exact_candidates_tested


def _search_exact_batches(
    node,
    target,
    ranked,
    *,
    limit,
    workers,
    batch_size,
    batch_timeout_seconds,
    max_local_steps=3,
):
    context = multiprocessing.get_context("fork")
    completed = 0
    timed_out = 0
    exact_target_candidates = 0
    selected = ranked[:limit]
    for batch_start in range(0, len(selected), batch_size):
        batch = selected[batch_start : batch_start + batch_size]
        print(
            json.dumps(
                {
                    "event": "exact_batch_start",
                    "batch_start": batch_start,
                    "batch_size": len(batch),
                    "best_first_residual": batch[0].first_residual,
                }
            ),
            file=sys.stderr,
            flush=True,
        )
        pool = context.Pool(
            processes=min(workers, len(batch)),
            initializer=_initialize_worker,
            initargs=(node, target, max_local_steps),
        )
        results = [
            pool.apply_async(
                _evaluate_first_step,
                ((row.index, row.candidate),),
            )
            for row in batch
        ]
        deadline = perf_counter() + batch_timeout_seconds
        hit = None
        for result in results:
            try:
                index, steps, _elapsed, tested = result.get(
                    timeout=max(0.0, deadline - perf_counter())
                )
            except multiprocessing.TimeoutError:
                timed_out += 1
                continue
            completed += 1
            exact_target_candidates += tested
            if steps is not None and hit is None:
                hit = (index, steps)
        if hit is not None or timed_out:
            pool.terminate()
        else:
            pool.close()
        pool.join()
        if hit is not None:
            return hit, completed, timed_out, exact_target_candidates
    return None, completed, timed_out, exact_target_candidates


def _canonical_candidate(node, step):
    first = next(point for point in node.state.points if point == step.first)
    second = next(point for point in node.state.points if point == step.second)
    return Candidate(step.op, first, second)


def run(args):
    started_at = perf_counter()
    initial, _prefix = exact_prefix("c_M1_2_Ay")
    target, known_tail = _target_and_tail()
    ranked = _numeric_first_step_scores(initial, target, args.workers)
    print(
        json.dumps(
            {
                "event": "numeric_ranking_end",
                "candidates": len(ranked),
                "best": [
                    {
                        "index": row.index,
                        "first_residual": row.first_residual,
                        "second_residual": row.second_residual,
                        "new_numeric_points": row.new_numeric_points,
                    }
                    for row in ranked[:5]
                ],
            }
        ),
        file=sys.stderr,
        flush=True,
    )
    hit, completed, timed_out, target_candidates_tested = (
        _search_exact_batches(
            initial,
            target,
            ranked,
            limit=args.first_step_limit,
            workers=args.workers,
            batch_size=args.batch_size,
            batch_timeout_seconds=args.batch_timeout_seconds,
        )
    )
    certificate_valid = None
    found_score = None
    if hit is not None:
        _index, local_steps = hit
        node = initial
        for candidate in local_steps:
            node = node.apply(_canonical_candidate(node, candidate))
        if not PointGoal(target).reached(node.state):
            raise RuntimeError("局部搜索返回的步骤没有精确构造 M0_4")
        for known_step in known_tail:
            node = node.apply(_canonical_candidate(node, known_step))
        certificate = build_certificate_from_steps(
            node.steps,
            profile_path=args.profile,
            construction_id="regular-17-m04-three-step-candidate",
            title="Regular 17-gon candidate from three-step M0_4 search",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(certificate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report = verify_files(args.output, args.profile)
        certificate_valid = report.valid
        found_score = node.score

    summary = {
        "schema": "euclid-min-m04-three-step-search/v1",
        "mode": "heuristic_nonproof",
        "prefix_e_move": initial.score,
        "local_budget": 3,
        "first_step_candidates": len(ranked),
        "first_step_limit": args.first_step_limit,
        "workers": args.workers,
        "batch_size": args.batch_size,
        "batch_timeout_seconds": args.batch_timeout_seconds,
        "exact_first_steps_completed": completed,
        "exact_first_steps_timed_out": timed_out,
        "exact_target_candidates_tested": target_candidates_tested,
        "found_local_steps": len(hit[1]) if hit is not None else None,
        "found_total_e_move": found_score,
        "certificate_valid": certificate_valid,
        "elapsed_seconds": perf_counter() - started_at,
        "interpretation_boundary": (
            "浮点第一步排序与固定 top-N 会删除分支；未命中只结束本次最终尝试。"
        ),
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if certificate_valid else 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT
    )
    parser.add_argument("--first-step-limit", type=int, default=128)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--batch-timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
