"""小深度、可审计的 Sage 精确搜索器。"""

from .candidates import generate_candidates
from .beam import DeterministicBeamSearch
from .parallel_beam import ParallelHeuristicBeamSearch
from .engine import BoundedBreadthFirstSearch
from .heuristic import (
    CandidateComplexityScore,
    OneMoveTargetHeuristic,
    PointDistanceHeuristic,
    Regular17CandidateHeuristic,
    Regular17Heuristic,
    Regular17OneMoveHeuristic,
)
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
    "CandidateComplexityScore",
    "DeterministicBeamSearch",
    "OneMoveTargetHeuristic",
    "ParallelHeuristicBeamSearch",
    "PointGoal",
    "PointDistanceHeuristic",
    "Regular17Goal",
    "Regular17CandidateHeuristic",
    "Regular17Heuristic",
    "Regular17OneMoveHeuristic",
    "SearchNode",
    "SearchOutcome",
    "SearchStats",
    "SearchStep",
    "generate_candidates",
]
