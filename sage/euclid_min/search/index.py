"""近似摘要分桶、精确确认的搜索状态索引。"""

from __future__ import annotations

import hashlib
import json

from ..state import GeometryState
from .symmetry import (
    reflect_circle_horizontal,
    reflect_line_horizontal,
    reflect_point_horizontal,
    states_equal_under_horizontal_reflection,
)


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


class HorizontalReflectionStateIndex:
    """把关于横轴互为镜像的精确状态合并为一个轨道。"""

    def __init__(self) -> None:
        self._buckets: dict[str, list[tuple[GeometryState, int]]] = {}

    def add_if_better(self, state: GeometryState, score: int) -> bool:
        digest = horizontal_reflection_fingerprint(state)
        bucket = self._buckets.setdefault(digest, [])
        for index, (existing, existing_score) in enumerate(bucket):
            equivalent = states_equal(existing, state) or (
                states_equal_under_horizontal_reflection(existing, state)
            )
            if not equivalent:
                continue
            if existing_score <= score:
                return False
            bucket[index] = (state, score)
            return True
        bucket.append((state, score))
        return True


def state_fingerprint(state: GeometryState) -> str:
    """返回确定性的非权威 SHA-256 分桶摘要。"""

    return _payload_fingerprint(_state_payload(state))


def horizontal_reflection_fingerprint(state: GeometryState) -> str:
    """返回状态及其横轴镜像两个分桶摘要中的字典序较小者。"""

    direct = state_fingerprint(state)
    reflected = _payload_fingerprint(_state_payload(state, reflected=True))
    return min(direct, reflected)


def _state_payload(state: GeometryState, *, reflected: bool = False) -> dict:
    points = (
        tuple(reflect_point_horizontal(point) for point in state.points)
        if reflected
        else state.points
    )
    lines = (
        tuple(reflect_line_horizontal(line) for line in state.lines)
        if reflected
        else state.lines
    )
    circles = (
        tuple(reflect_circle_horizontal(circle) for circle in state.circles)
        if reflected
        else state.circles
    )
    return {
        "points": sorted(
            (_float_token(point.x), _float_token(point.y))
            for point in points
        ),
        "lines": sorted(
            (
                _float_token(line.a),
                _float_token(line.b),
                _float_token(line.c),
            )
            for line in lines
        ),
        "circles": sorted(
            (
                _float_token(circle.center.x),
                _float_token(circle.center.y),
                _float_token(circle.radius_squared),
            )
            for circle in circles
        ),
    }


def _payload_fingerprint(payload: dict) -> str:
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
    if value == 0:
        return float(0).hex()
    return float(value).hex()
