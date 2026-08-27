"""近似摘要分桶、精确确认的搜索状态索引。"""

from __future__ import annotations

import hashlib
import json

from ..state import GeometryState


class ExactStateIndex:
    """摘要从不充当相等证明；桶内总是逐对象精确确认。"""

    def __init__(self) -> None:
        self._buckets: dict[str, list[tuple[GeometryState, int]]] = {}

    def add_if_better(self, state: GeometryState, score: int) -> bool:
        digest = state_fingerprint(state)
        bucket = self._buckets.setdefault(digest, [])
        for index, (existing, existing_score) in enumerate(bucket):
            if not states_equal(existing, state):
                continue
            if existing_score <= score:
                return False
            bucket[index] = (state, score)
            return True
        bucket.append((state, score))
        return True


def state_fingerprint(state: GeometryState) -> str:
    """返回确定性的非权威 SHA-256 分桶摘要。"""

    payload = {
        "points": sorted(
            (_float_token(point.x), _float_token(point.y))
            for point in state.points
        ),
        "lines": sorted(
            (
                _float_token(line.a),
                _float_token(line.b),
                _float_token(line.c),
            )
            for line in state.lines
        ),
        "circles": sorted(
            (
                _float_token(circle.center.x),
                _float_token(circle.center.y),
                _float_token(circle.radius_squared),
            )
            for circle in state.circles
        ),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def states_equal(first: GeometryState, second: GeometryState) -> bool:
    """忽略插入顺序，精确比较 (P,L,C) 三个数学集合。"""

    return (
        _sets_equal(first.points, second.points)
        and _sets_equal(first.lines, second.lines)
        and _sets_equal(first.circles, second.circles)
    )


def _sets_equal(first: tuple, second: tuple) -> bool:
    if len(first) != len(second):
        return False
    return all(any(item == candidate for candidate in second) for item in first)


def _float_token(value) -> str:
    return float(value).hex()
