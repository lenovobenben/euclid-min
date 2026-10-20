from __future__ import annotations

import unittest

from euclid_min.geometry import Point
from euclid_min.search import Candidate, SearchNode
from euclid_min.search.incidence import (
    generate_terminal_candidates_using_new_points_strict,
    generate_terminal_candidates_with_deferred_incidence,
    new_points_on_existing_drawable,
)
from euclid_min.target import TargetName, adjacent_targets


class StrictIncidenceTests(unittest.TestCase):
    def test_interval_and_exact_paths_recover_a_target_using_a_new_intersection(self):
        state = SearchNode.initial().state
        target = adjacent_targets()[TargetName.B_PLUS]
        first, second = Point(-1, 1), Point(-1, 2)
        anchor = Point(2 * target.x + 1, 2 * target.y)
        # Synthetic inputs isolate the exact incidence algorithm.
        for point in (first, second, anchor):
            state._add_point(point)
        child = state.clone()
        addition = child.draw_line(first, second)
        exact, _audit = generate_terminal_candidates_using_new_points_strict(child, addition.new_points)
        on_unit_circle = new_points_on_existing_drawable(state, addition, state.circles[0])
        interval = generate_terminal_candidates_with_deferred_incidence(
            child, addition.new_points, new_unit_circle_points=on_unit_circle,
        )
        expected = Candidate("line", Point(-1, 0), anchor).drawable()
        self.assertEqual(interval.candidates, exact)
        self.assertEqual(interval.deferred, ())
        self.assertTrue(any(candidate.drawable() == expected for candidate in exact))
