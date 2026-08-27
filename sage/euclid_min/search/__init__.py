"""小深度、可审计的 Sage 精确搜索器。"""

from .candidates import generate_candidates
from .engine import BoundedBreadthFirstSearch
from .model import (
    Candidate,
    PointGoal,
    Regular17Goal,
    SearchNode,
    SearchOutcome,
    SearchStats,
    SearchStep,
)

__all__ = [
    "BoundedBreadthFirstSearch",
    "Candidate",
    "PointGoal",
    "Regular17Goal",
    "SearchNode",
    "SearchOutcome",
    "SearchStats",
    "SearchStep",
    "generate_candidates",
]
