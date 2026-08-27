from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sage.all import AA

from euclid_min.geometry import Point
from euclid_min.replay import ProgramReplayer
from euclid_min.search import (
    BoundedBreadthFirstSearch,
    PointGoal,
    SearchNode,
    generate_candidates,
)
from euclid_min.search.export import build_program_from_steps
from euclid_min.search.checkpoint import load_checkpoint, save_checkpoint
from euclid_min.search.index import ExactStateIndex, state_fingerprint, states_equal


class CandidateGenerationTests(unittest.TestCase):
    def test_initial_candidates_are_complete_and_deterministic(self):
        candidates = generate_candidates(SearchNode.initial().state)
        self.assertEqual([candidate.op for candidate in candidates], ["line", "circle"])
        self.assertEqual(candidates[0].first, Point(0, 0))
        self.assertEqual(candidates[0].second, Point(1, 0))
        self.assertEqual(candidates[1].first, Point(1, 0))
        self.assertEqual(candidates[1].second, Point(0, 0))


class StateIndexTests(unittest.TestCase):
    def test_operation_order_is_removed_only_after_exact_confirmation(self):
        initial = SearchNode.initial()
        candidates = generate_candidates(initial.state)
        line_first = initial.apply(candidates[0])
        circle_first = initial.apply(candidates[1])

        line_then_circle = line_first.apply(
            next(
                candidate
                for candidate in generate_candidates(line_first.state)
                if candidate.op == "circle"
                and candidate.first == Point(1, 0)
                and candidate.second == Point(0, 0)
            )
        )
        circle_then_line = circle_first.apply(
            next(
                candidate
                for candidate in generate_candidates(circle_first.state)
                if candidate.op == "line"
                and candidate.drawable() == candidates[0].drawable()
            )
        )

        self.assertTrue(states_equal(line_then_circle.state, circle_then_line.state))
        self.assertEqual(
            state_fingerprint(line_then_circle.state),
            state_fingerprint(circle_then_line.state),
        )
        index = ExactStateIndex()
        self.assertTrue(index.add_if_better(line_then_circle.state, 2))
        self.assertFalse(index.add_if_better(circle_then_line.state, 2))


class SearchEngineTests(unittest.TestCase):
    def test_rediscovers_equilateral_vertex_in_one_move(self):
        root_three_over_two = AA(3).sqrt() / 2
        goal = PointGoal(Point(AA(1) / 2, root_three_over_two))
        outcome = BoundedBreadthFirstSearch().search(goal, max_score=1)
        self.assertEqual(outcome.status, "found")
        self.assertIsNotNone(outcome.node)
        self.assertEqual(outcome.node.score, 1)
        self.assertEqual(outcome.node.steps[0].op, "circle")

    def test_rediscovers_midpoint_and_exports_replayable_program(self):
        goal = PointGoal(Point(AA(1) / 2, 0))
        outcome = BoundedBreadthFirstSearch().search(
            goal,
            max_score=3,
            max_states=1000,
        )
        self.assertEqual(outcome.status, "found")
        self.assertIsNotNone(outcome.node)
        self.assertEqual(outcome.node.score, 3)

        program, state = build_program_from_steps(outcome.node.steps)
        replay = ProgramReplayer().replay(program)
        self.assertEqual(replay.e_move, 3)
        self.assertTrue(state.contains_point(Point(AA(1) / 2, 0)))

    def test_state_limit_is_reported_without_claiming_exhaustion(self):
        goal = PointGoal(Point(AA(1) / 3, 0))
        outcome = BoundedBreadthFirstSearch().search(
            goal,
            max_score=3,
            max_states=1,
        )
        self.assertEqual(outcome.status, "state_limit")
        self.assertIsNone(outcome.node)
        self.assertTrue(outcome.frontier)

    def test_checkpoint_round_trip_resumes_without_losing_frontier(self):
        midpoint = PointGoal(Point(AA(1) / 2, 0))
        first_run = BoundedBreadthFirstSearch().search(
            midpoint,
            max_score=3,
            max_states=1,
        )
        self.assertEqual(first_run.status, "state_limit")

        repository_root = Path(__file__).resolve().parents[2]
        profile_path = repository_root / "profiles" / "regular-17-e-fixed-v1.yaml"
        with TemporaryDirectory() as temporary_directory:
            checkpoint_path = Path(temporary_directory) / "search.json"
            save_checkpoint(
                checkpoint_path,
                profile_path=profile_path,
                max_score=3,
                frontier=first_run.frontier,
                stats=first_run.stats,
            )
            checkpoint = load_checkpoint(
                checkpoint_path,
                profile_path=profile_path,
            )

        self.assertEqual(checkpoint.max_score, 3)
        self.assertEqual(len(checkpoint.frontier), len(first_run.frontier))
        resumed = BoundedBreadthFirstSearch().search(
            midpoint,
            max_score=checkpoint.max_score,
            max_states=1000,
            initial_frontier=checkpoint.frontier,
        )
        self.assertEqual(resumed.status, "found")
        self.assertEqual(resumed.node.score, 3)


if __name__ == "__main__":
    unittest.main()
