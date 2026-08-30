"""从完整精确点集确定性生成基础操作候选。"""

from __future__ import annotations

from collections.abc import Callable

from ..geometry import Circle, Drawable, Line, Point
from ..state import GeometryState
from .model import Candidate


def generate_candidates(state: GeometryState) -> tuple[Candidate, ...]:
    """生成所有不同的新对象，每个数学对象只保留第一种点对表示。"""

    points = tuple(sorted(state.points))
    candidates: list[Candidate] = []
    object_index = _CandidateObjectIndex(state.drawables)

    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            line = Line.through(first, second)
            if not object_index.add_if_new(line):
                continue
            candidates.append(Candidate("line", first, second))

    for center in points:
        for through in points:
            if center == through:
                continue
            circle = Circle.through(center, through)
            if not object_index.add_if_new(circle):
                continue
            candidates.append(Candidate("circle", center, through))

    return tuple(candidates)


def generate_prefiltered_candidates(
    state: GeometryState,
    *,
    limit: int,
    score_operation: Callable[[str, Point, Point], object],
    operation_key: Callable[[str, Point, Point], object] | None = None,
    operation_level: Callable[[str, Point, Point], int] | None = None,
    exact_deduplicate: bool = True,
    diversify: bool = False,
) -> tuple[tuple[Candidate, ...], int, int]:
    """先对点对操作做浮点评分，再精确构造至多 ``limit`` 个候选。

    第二项是原始点对操作数，第三项是通过可选复杂度门后参与排序的操作数。
    该模式会永久删除分支，只能用于明确标记为非证明的启发式搜索。
    """

    if limit < 1:
        raise ValueError("候选预筛上限至少为 1")
    points = tuple(sorted(state.points))
    ranked: list[tuple[object, int, object, int, str, Point, Point]] = []
    sequence = 0
    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            score = score_operation("line", first, second)
            sequence += 1
            if score is None:
                continue
            ranked.append(
                (
                    score,
                    sequence,
                    (
                        operation_key("line", first, second)
                        if operation_key is not None
                        else None
                    ),
                    (
                        operation_level("line", first, second)
                        if operation_level is not None
                        else 0
                    ),
                    "line",
                    first,
                    second,
                )
            )
    for center in points:
        for through in points:
            if center == through:
                continue
            score = score_operation("circle", center, through)
            sequence += 1
            if score is None:
                continue
            ranked.append(
                (
                    score,
                    sequence,
                    (
                        operation_key("circle", center, through)
                        if operation_key is not None
                        else None
                    ),
                    (
                        operation_level("circle", center, through)
                        if operation_level is not None
                        else 0
                    ),
                    "circle",
                    center,
                    through,
                )
            )
    ranked.sort(key=lambda item: (item[0], item[1]))

    selected: list[Candidate] = []
    object_index = (
        _CandidateObjectIndex(state.drawables) if exact_deduplicate else None
    )
    seen_operation_keys: set[object] = set()
    rows = (
        _diversified_rows(ranked, limit)
        if diversify and not exact_deduplicate
        else ranked
    )
    for _score, _sequence, key, _level, op, first, second in rows:
        candidate = Candidate(op, first, second)
        if exact_deduplicate:
            if not object_index.add_if_new(candidate.drawable()):
                continue
        elif key is not None:
            if key in seen_operation_keys:
                continue
            seen_operation_keys.add(key)
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return tuple(selected), sequence, len(ranked)


def _diversified_rows(ranked: list[tuple], limit: int) -> list[tuple]:
    """混合近目标候选、低层级直线和低层级圆。"""

    target_quota = max(1, limit // 2)
    remaining = limit - target_quota
    line_quota = remaining // 2
    circle_quota = remaining - line_quota
    cheap_lines = sorted(
        (row for row in ranked if row[4] == "line"),
        key=lambda row: (row[3], row[0], row[1]),
    )
    cheap_circles = sorted(
        (row for row in ranked if row[4] == "circle"),
        key=lambda row: (row[3], row[0], row[1]),
    )
    selected: list[tuple] = []
    seen: set[object] = set()

    def take(rows: list[tuple], quota: int) -> None:
        if quota <= 0:
            return
        added = 0
        for row in rows:
            key = row[2]
            if key in seen:
                continue
            seen.add(key)
            selected.append(row)
            added += 1
            if added >= quota:
                break

    take(ranked, target_quota)
    take(cheap_lines, line_quota)
    take(cheap_circles, circle_quota)
    if len(selected) < limit:
        take(ranked, limit - len(selected))
    return selected


class _CandidateObjectIndex:
    """用数值摘要分桶、再以精确相等确认候选对象去重。"""

    def __init__(self, objects: tuple[Drawable, ...]) -> None:
        self._buckets: dict[tuple[str, ...], list[Drawable]] = {}
        for item in objects:
            self._buckets.setdefault(_object_key(item), []).append(item)

    def add_if_new(self, candidate: Drawable) -> bool:
        bucket = self._buckets.setdefault(_object_key(candidate), [])
        if any(
            type(item) is type(candidate) and item == candidate
            for item in bucket
        ):
            return False
        bucket.append(candidate)
        return True


def _object_key(candidate: Drawable) -> tuple[str, ...]:
    """相等对象必有相同键；摘要碰撞不会跳过精确确认。"""

    if isinstance(candidate, Line):
        return (
            "line",
            float(candidate.a).hex(),
            float(candidate.b).hex(),
            float(candidate.c).hex(),
        )
    return (
        "circle",
        float(candidate.center.x).hex(),
        float(candidate.center.y).hex(),
        float(candidate.radius_squared).hex(),
    )
