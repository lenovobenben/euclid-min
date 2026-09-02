from __future__ import annotations

import json
import unittest

from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import node_from_steps, steps_from_program
from euclid_min.search.incidence import (
    generate_terminal_candidates_using_new_points_strict,
    generate_terminal_candidates_with_deferred_incidence,
    new_points_on_existing_drawable,
)
from experiments.build_regular17_geometry_algebra_ir import CERTIFICATE_PATH
from experiments.search_e16_two_step_target_extension import (
    _apply_precursor,
    _program_prefix,
)


class StrictIncidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
        prefix = _program_prefix(certificate["construction"]["program"], 16)
        cls.state = node_from_steps(steps_from_program(prefix)).state
        cls.candidates = generate_candidates(cls.state)

    def test_interval_path_matches_exact_path_and_skips_unit_circle_duplicate(self):
        precursor = self.candidates[1472]
        child, addition = _apply_precursor(self.state, precursor)
        exact, exact_audit = generate_terminal_candidates_using_new_points_strict(
            child,
            addition.new_points,
        )
        unit_points = new_points_on_existing_drawable(
            self.state,
            addition,
            self.state.circles[0],
        )
        interval = generate_terminal_candidates_with_deferred_incidence(
            child,
            addition.new_points,
            new_unit_circle_points=unit_points,
        )
        self.assertEqual(interval.candidates, exact)
        self.assertEqual(interval.deferred, ())
        self.assertEqual(exact_audit.exact_fallbacks, 2)
        self.assertEqual(exact_audit.exact_zeros, 2)
        self.assertEqual(interval.audit.exact_fallbacks, 0)
        self.assertEqual(interval.audit.structural_existing_objects, 2)


if __name__ == "__main__":
    unittest.main()
