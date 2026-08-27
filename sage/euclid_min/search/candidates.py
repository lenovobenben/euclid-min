"""从完整精确点集确定性生成基础操作候选。"""

from __future__ import annotations

from ..geometry import Circle, Drawable, Line
from ..state import GeometryState
from .model import Candidate


def generate_candidates(state: GeometryState) -> tuple[Candidate, ...]:
    """生成所有不同的新对象，每个数学对象只保留第一种点对表示。"""

    points = tuple(sorted(state.points))
    candidates: list[Candidate] = []
    candidate_objects: list[Drawable] = []

    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            line = Line.through(first, second)
            if state.contains_line(line) or _contains(candidate_objects, line):
                continue
            candidates.append(Candidate("line", first, second))
            candidate_objects.append(line)

    for center in points:
        for through in points:
            if center == through:
                continue
            circle = Circle.through(center, through)
            if state.contains_circle(circle) or _contains(
                candidate_objects, circle
            ):
                continue
            candidates.append(Candidate("circle", center, through))
            candidate_objects.append(circle)

    return tuple(candidates)


def _contains(objects: list[Drawable], candidate: Drawable) -> bool:
    return any(type(item) is type(candidate) and item == candidate for item in objects)
