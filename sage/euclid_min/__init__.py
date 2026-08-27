"""Euclid-Min 的 SageMath 精确参考内核。"""

from .geometry import Circle, Line, Point
from .intersections import IntersectionKind, IntersectionResult, intersect
from .state import AdditionResult, GeometryState
from .target import TargetName, adjacent_targets, reached_targets
from .version import __version__

__all__ = [
    "AdditionResult",
    "Circle",
    "GeometryState",
    "IntersectionKind",
    "IntersectionResult",
    "Line",
    "Point",
    "TargetName",
    "adjacent_targets",
    "intersect",
    "reached_targets",
    "__version__",
]
