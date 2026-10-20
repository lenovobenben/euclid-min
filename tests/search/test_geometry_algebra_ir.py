from __future__ import annotations

import json
import unittest
from pathlib import Path

from sage.all import QQ

from euclid_min.geometry_algebra_ir import (
    add, divide, evaluate_expression, expression_symbol_ids,
    multiply, rational, replay_full_closure, subtract,
)


ROOT = Path(__file__).resolve().parents[2]


class GeometryAlgebraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        certificate = json.loads((ROOT / "qq-ggb/construction-12e-011.json").read_text())
        program = certificate["construction"]["program"]
        # This prefix exercises an intersection born before it is named.
        end = next(i for i, entry in enumerate(program) if entry["id"] == "ggb_I")
        cls.replay = replay_full_closure(program[:end])

    def test_transition_inputs_are_available_before_drawing(self):
        self.assertEqual([row["e_move"] for row in self.replay.transitions], list(range(1, 7)))
        for row in self.replay.transitions:
            self.assertTrue(all(birth < row["e_move"] for birth in row["definition_point_birth_e_moves"]))

    def test_free_intersection_precedes_its_certificate_binding(self):
        self.assertEqual(self.replay.point_record("ggb_H").birth_e_move, 2)
        self.assertEqual(self.replay.explicit_binding_e_moves["ggb_H"], 5)
        self.assertGreater(len(self.replay.points), len(self.replay.names) - len(self.replay.drawables))

    def test_expression_tree_is_exact_and_tracks_dependencies(self):
        expression = divide(subtract(multiply("x", "x"), rational(1, 4)), add("x", 1))
        self.assertEqual(expression_symbol_ids(expression), {"x"})
        self.assertEqual(evaluate_expression(expression, {"x": QQ(1)/2}), 0)
        self.assertEqual(evaluate_expression(expression, {"x": QQ(2)}), QQ(5)/4)
        with self.assertRaises(ZeroDivisionError):
            evaluate_expression(expression, {"x": QQ(-1)})
