from __future__ import annotations

import unittest

from euclid_min.errors import VerificationError
from euclid_min.geometry import Point
from euclid_min.replay import ProgramReplayer


class ProgramReplayTests(unittest.TestCase):
    def test_replay_tracks_aliases_duplicates_closure_and_score(self):
        program = [
            {"id": "l1", "op": "line", "through": ["O", "A"]},
            {"id": "l2", "op": "line", "through": ["O", "A"]},
            {
                "id": "P",
                "op": "intersect",
                "objects": ["l2", "unit_circle"],
                "index": 0,
            },
            {"id": "c1", "op": "circle", "center": "A", "through": "P"},
        ]
        result = ProgramReplayer().replay(program)
        self.assertEqual(result.line_draws, 2)
        self.assertEqual(result.circle_draws, 1)
        self.assertEqual(result.e_move, 3)
        self.assertEqual(result.duplicate_draws, 1)
        self.assertEqual(result.names["P"], Point(-1, 0))
        self.assertEqual(len(result.state.lines), 1)
        self.assertEqual(len(result.state.circles), 2)
        self.assertEqual(len(result.state.points), 3)
        self.assertEqual(result.targets, ())

    def test_unknown_reference_reports_program_location(self):
        error = self._replay_error(
            [{"id": "l1", "op": "line", "through": ["O", "missing"]}]
        )
        self.assertEqual(error.code, "unknown_reference")
        self.assertEqual(error.program_index, 0)
        self.assertEqual(error.entry_id, "l1")
        self.assertEqual(error.details["consumed_e_moves_before_error"], 0)

    def test_wrong_reference_type_is_rejected(self):
        error = self._replay_error(
            [{"id": "l1", "op": "line", "through": ["O", "unit_circle"]}]
        )
        self.assertEqual(error.code, "wrong_reference_type")

    def test_duplicate_id_is_rejected(self):
        error = self._replay_error(
            [{"id": "O", "op": "line", "through": ["O", "A"]}]
        )
        self.assertEqual(error.code, "duplicate_id")

    def test_distinct_aliases_of_same_point_are_coincident_inputs(self):
        program = [
            {"id": "l1", "op": "line", "through": ["O", "A"]},
            {
                "id": "A2",
                "op": "intersect",
                "objects": ["l1", "unit_circle"],
                "index": 1,
            },
            {"id": "bad", "op": "line", "through": ["A", "A2"]},
        ]
        error = self._replay_error(program)
        self.assertEqual(error.code, "coincident_input_points")
        self.assertEqual(error.details["consumed_e_moves_before_error"], 1)

    def test_coincident_object_aliases_have_no_selectable_intersection(self):
        program = [
            {"id": "l1", "op": "line", "through": ["O", "A"]},
            {"id": "l2", "op": "line", "through": ["O", "A"]},
            {
                "id": "bad",
                "op": "intersect",
                "objects": ["l1", "l2"],
                "index": 0,
            },
        ]
        error = self._replay_error(program)
        self.assertEqual(error.code, "coincident_intersection_objects")
        self.assertEqual(error.details["consumed_e_moves_before_error"], 2)

    def test_intersection_index_out_of_range(self):
        program = [
            {"id": "l1", "op": "line", "through": ["O", "A"]},
            {
                "id": "P",
                "op": "intersect",
                "objects": ["l1", "unit_circle"],
                "index": 0,
            },
            {"id": "c1", "op": "circle", "center": "A", "through": "P"},
            {
                "id": "bad",
                "op": "intersect",
                "objects": ["c1", "unit_circle"],
                "index": 1,
            },
        ]
        error = self._replay_error(program)
        self.assertEqual(error.code, "intersection_index_out_of_range")
        self.assertEqual(error.details["intersection_count"], 1)

    def _replay_error(self, program):
        with self.assertRaises(VerificationError) as caught:
            ProgramReplayer().replay(program)
        return caught.exception


if __name__ == "__main__":
    unittest.main()
