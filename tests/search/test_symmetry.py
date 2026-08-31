from __future__ import annotations

import unittest

from euclid_min.geometry import Circle, Line, Point
from euclid_min.search import SearchNode, generate_candidates
from euclid_min.search.index import (
    HorizontalReflectionStateIndex,
    horizontal_reflection_fingerprint,
    states_equal,
)
from euclid_min.search.model import Candidate
from euclid_min.search.symmetry import (
    reflect_circle_horizontal,
    reflect_line_horizontal,
    reflect_point_horizontal,
    states_equal_under_horizontal_reflection,
)
from euclid_min.target import TargetName, adjacent_targets


class HorizontalReflectionTests(unittest.TestCase):
    def test_reflection_is_an_involution_and_commutes_with_drawables(self):
        first = Point(2, 3)
        second = Point(-1, 5)

        reflected_first = reflect_point_horizontal(first)
        reflected_second = reflect_point_horizontal(second)
        self.assertEqual(reflect_point_horizontal(reflected_first), first)
        self.assertEqual(
            reflect_line_horizontal(Line.through(first, second)),
            Line.through(reflected_first, reflected_second),
        )
        self.assertEqual(
            reflect_circle_horizontal(Circle.through(first, second)),
            Circle.through(reflected_first, reflected_second),
        )

    def test_reflection_swaps_the_two_accepted_targets(self):
        targets = adjacent_targets()
        self.assertEqual(
            reflect_point_horizontal(targets[TargetName.B_PLUS]),
            targets[TargetName.B_MINUS],
        )
        self.assertEqual(
            reflect_point_horizontal(targets[TargetName.B_MINUS]),
            targets[TargetName.B_PLUS],
        )

    def test_mirrored_states_share_one_exact_orbit(self):
        initial = SearchNode.initial()
        circle_candidate = next(
            candidate
            for candidate in generate_candidates(initial.state)
            if candidate.op == "circle"
        )
        circle_node = initial.apply(circle_candidate)
        origin = Point(0, 0)
        upper = max(circle_node.state.points, key=lambda point: point.y)
        lower = min(circle_node.state.points, key=lambda point: point.y)

        upper_node = circle_node.apply(Candidate("line", origin, upper))
        lower_node = circle_node.apply(Candidate("line", origin, lower))

        self.assertFalse(states_equal(upper_node.state, lower_node.state))
        self.assertTrue(
            states_equal_under_horizontal_reflection(
                upper_node.state,
                lower_node.state,
            )
        )
        self.assertEqual(
            horizontal_reflection_fingerprint(upper_node.state),
            horizontal_reflection_fingerprint(lower_node.state),
        )

        index = HorizontalReflectionStateIndex()
        self.assertTrue(index.add_if_better(upper_node.state, upper_node.score))
        self.assertFalse(index.add_if_better(lower_node.state, lower_node.score))


if __name__ == "__main__":
    unittest.main()
