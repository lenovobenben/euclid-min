from __future__ import annotations

import json
import unittest
from pathlib import Path

from euclid_min.geometry import Point
from euclid_min.replay import ProgramReplayer
from euclid_min.search import Candidate, SearchNode
from euclid_min.search.backward import (
    build_regular17_two_step_obligation,
    expand_regular17_precursor_obligation,
    expand_regular17_two_step_obligations,
    generate_regular17_terminal_candidates,
    generate_regular17_terminal_candidates_direct,
    generate_regular17_terminal_candidates_using_new_points,
    is_regular17_terminal_step,
    regular17_targets_on_step,
    terminal_parameterizations_using_new_points,
)
from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import node_from_steps, steps_from_program
from euclid_min.target import TargetName, adjacent_targets


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMPROVED_CERTIFICATE = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)


class BackwardTerminalConstraintTests(unittest.TestCase):
    def test_initial_state_has_no_one_move_terminal_candidate(self):
        state = SearchNode.initial().state
        self.assertEqual(generate_regular17_terminal_candidates(state), ())
        self.assertEqual(
            generate_regular17_terminal_candidates_direct(state),
            (),
        )

    def test_direct_terminal_generation_matches_full_filter(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        program = certificate["construction"]["program"]
        target_line_index = next(
            index
            for index, entry in enumerate(program)
            if entry["id"] == "target_line"
        )
        state = ProgramReplayer().replay(program[:target_line_index]).state

        filtered = generate_regular17_terminal_candidates(state)
        direct = generate_regular17_terminal_candidates_direct(state)

        self.assertEqual(direct, filtered)
        self.assertGreaterEqual(len(direct), 1)
        known_final_step = steps_from_program(program)[-1]
        self.assertTrue(
            any(candidate.drawable() == known_final_step.drawable() for candidate in direct)
        )

    def test_known_19e_path_first_gets_target_on_its_last_step(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        steps = steps_from_program(certificate["construction"]["program"])

        self.assertEqual(len(steps), 19)
        self.assertTrue(all(not is_regular17_terminal_step(step) for step in steps[:-1]))
        self.assertTrue(is_regular17_terminal_step(steps[-1]))
        self.assertEqual(
            regular17_targets_on_step(steps[-1]),
            (TargetName.B_PLUS,),
        )

    def test_initial_two_step_and_or_expansion_is_exhaustive_and_empty(self):
        state = SearchNode.initial().state
        expansion = expand_regular17_two_step_obligations(state)

        self.assertEqual(
            expansion.precursor_candidates,
            len(generate_candidates(state)),
        )
        self.assertGreater(expansion.terminal_parameterizations_tested, 0)
        self.assertEqual(expansion.terminal_candidates, 0)
        self.assertFalse(expansion.reaches_target_within_two_steps)

    def test_two_step_expansion_records_new_point_intersection_support(self):
        target = adjacent_targets()[TargetName.B_PLUS]
        state = SearchNode.initial().state
        first = Point(-1, 1)
        second = Point(-1, 2)
        terminal_anchor = Point(2 * target.x + 1, 2 * target.y)
        for point in (first, second, terminal_anchor):
            state._add_point(point)

        precursor_drawable = Candidate("line", first, second).drawable()
        branch = expand_regular17_precursor_obligation(
            state,
            Candidate("line", first, second),
        )
        self.assertEqual(branch.candidate.drawable(), precursor_drawable)
        new_point = Point(-1, 0)
        terminal_drawable = Candidate(
            "line",
            new_point,
            terminal_anchor,
        ).drawable()
        alternative = next(
            alternative
            for alternative in branch.terminal_alternatives
            if alternative.candidate.drawable() == terminal_drawable
        )

        self.assertEqual(alternative.targets, (TargetName.B_PLUS,))
        self.assertEqual(alternative.required_points, (new_point, terminal_anchor))
        self.assertEqual(len(alternative.new_input_origins), 1)
        origin = alternative.new_input_origins[0]
        self.assertEqual(origin.point, new_point)
        self.assertEqual(origin.supporting_drawables, state.circles)

    def test_known_19e_last_two_draws_form_a_valid_and_branch(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        program = certificate["construction"]["program"]
        replay = ProgramReplayer().replay(program)
        steps = steps_from_program(program)
        state = node_from_steps(steps[:17]).state
        precursor = Candidate(
            steps[17].op,
            steps[17].first,
            steps[17].second,
        )
        terminal = Candidate(
            steps[18].op,
            steps[18].first,
            steps[18].second,
        )

        obligation = build_regular17_two_step_obligation(
            state,
            precursor,
            terminal,
        )

        self.assertEqual(obligation.targets, (TargetName.B_PLUS,))
        self.assertEqual(len(obligation.new_input_origins), 1)
        origin = obligation.new_input_origins[0]
        self.assertEqual(origin.point, replay.names["target_helper_point"])
        self.assertTrue(
            any(
                drawable == replay.names["c_Q_O"]
                for drawable in origin.supporting_drawables
            )
        )

    def test_new_point_terminal_restriction_recovers_known_final_step(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        steps = steps_from_program(certificate["construction"]["program"])
        state = node_from_steps(steps[:17]).state
        self.assertEqual(generate_regular17_terminal_candidates_direct(state), ())

        precursor = Candidate(
            steps[17].op,
            steps[17].first,
            steps[17].second,
        )
        child = state.clone()
        addition = child.draw_circle(precursor.first, precursor.second)
        self.assertTrue(addition.new_object)
        full = generate_regular17_terminal_candidates_direct(child)
        restricted = generate_regular17_terminal_candidates_using_new_points(
            child,
            addition.new_points,
        )

        self.assertEqual(restricted, full)
        self.assertTrue(
            any(
                candidate.drawable() == steps[18].drawable()
                for candidate in restricted
            )
        )
        restricted_count = terminal_parameterizations_using_new_points(
            child,
            addition.new_points,
        )
        full_count = 3 * len(child.points) * (len(child.points) - 1) // 2
        self.assertLess(restricted_count, full_count)


if __name__ == "__main__":
    unittest.main()
