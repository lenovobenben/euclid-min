"""小深度、可审计的 Sage 精确搜索器。"""

from .candidates import generate_candidates
from .backward import (
    generate_regular17_terminal_candidates,
    is_regular17_terminal_step,
    regular17_targets_on_step,
)
from .dependencies import (
    PaidAncestryAudit,
    audit_first_target_ancestry,
    audit_paid_ancestry,
    dependency_ancestors,
    first_target_draw_id,
    prune_program_to_ancestors,
)
from .beam import DeterministicBeamSearch
from .parallel_beam import ParallelHeuristicBeamSearch
from .proof import (
    build_bounded_proof,
    check_bounded_proof,
    enumerate_bounded_proof,
    save_bounded_proof,
)
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
    "PaidAncestryAudit",
    "PointDistanceHeuristic",
    "Regular17Goal",
    "Regular17CandidateHeuristic",
    "Regular17Heuristic",
    "Regular17OneMoveHeuristic",
    "SearchNode",
    "SearchOutcome",
    "SearchStats",
    "SearchStep",
    "audit_first_target_ancestry",
    "audit_paid_ancestry",
    "build_bounded_proof",
    "check_bounded_proof",
    "dependency_ancestors",
    "enumerate_bounded_proof",
    "first_target_draw_id",
    "generate_regular17_terminal_candidates",
    "generate_candidates",
    "is_regular17_terminal_step",
    "prune_program_to_ancestors",
    "regular17_targets_on_step",
    "save_bounded_proof",
]
