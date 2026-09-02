from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from experiments.build_regular17_geometry_algebra_ir import (
    CERTIFICATE_PATH,
    OUTPUT_PATH,
    REPOSITORY_ROOT,
    load_and_build,
)


SCHEMA_PATH = REPOSITORY_ROOT / "schemas" / "geometry-algebra-ir-v1.schema.json"


class Regular17GeometryAlgebraIRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = load_and_build()

    def test_schema_and_deterministic_regeneration(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_source_hash_and_19e_contextual_cost(self):
        self.assertEqual(
            self.committed["source"]["certificate_sha256"],
            hashlib.sha256(CERTIFICATE_PATH.read_bytes()).hexdigest(),
        )
        audit = self.committed["cost_audit"]
        self.assertEqual(audit["charged_e_move"], 19)
        self.assertEqual(audit["contextual_new_object_e_move"], 19)
        self.assertEqual((audit["lines"], audit["circles"]), (8, 11))
        self.assertEqual(audit["full_closure_points"], 180)
        self.assertEqual(audit["explicit_intersection_bindings"], 22)
        self.assertEqual(audit["unbound_free_closure_points"], 156)

    def test_transition_schedule_uses_true_point_birth(self):
        transitions = self.committed["transitions"]
        self.assertEqual(
            [transition["e_move"] for transition in transitions],
            list(range(1, 20)),
        )
        self.assertTrue(
            all(
                birth < transition["e_move"]
                for transition in transitions
                for birth in transition["definition_point_birth_e_moves"]
            )
        )
        by_drawable = {
            transition["drawable"]: transition for transition in transitions
        }
        self.assertEqual(
            by_drawable["c_direct_y"]["definition_point_birth_e_moves"],
            [7, 12],
        )
        self.assertIn(
            "positive_half",
            by_drawable["c_direct_y"]["explicit_bindings_after_draw"],
        )

    def test_exact_quadratic_tower_and_free_target_trace(self):
        relations = self.committed["algebraic_relations"]
        self.assertEqual(len(relations), 6)
        self.assertTrue(all(relation["verified"] for relation in relations))
        by_representation = {
            item["id"]: item for item in self.committed["representations"]
        }
        target_trace = by_representation["repr.auto.H0_8.x"]
        self.assertEqual(target_trace["symbol"], "period.eta0_8")
        self.assertEqual(target_trace["available_e_move"], 17)
        self.assertNotIn("reference", target_trace["carrier"])
        target_point = by_representation["repr.target.B_plus.twice-x"]
        self.assertEqual(target_point["available_e_move"], 19)
        self.assertTrue(
            self.committed["consistency"]["target_bridge"]["verified"]
        )

    def test_live_slice_distinguishes_consumed_and_free_roots(self):
        live = self.committed["live_slice"]["algebraic"]
        self.assertEqual(len(live["active_relations"]), 6)
        self.assertEqual(
            live["free_sibling_roots"],
            ["period.eta0_8", "period.eta2_4", "period.eta3_4"],
        )
        self.assertEqual(
            live["target_relevant_free_roots"], ["period.eta0_8"]
        )
        geometry = self.committed["live_slice"]["geometry"]
        self.assertTrue(geometry["all_paid_objects_live"])
        self.assertEqual(len(geometry["live_paid_objects"]), 19)

    def test_macro_partition_covers_every_paid_draw_once(self):
        macros = self.committed["baseline_macro_partition"]
        self.assertEqual(sum(item["observed_charged_cost_e"] for item in macros), 19)
        self.assertEqual(
            [drawable for item in macros for drawable in item["paid_drawables"]],
            [transition["drawable"] for transition in self.committed["transitions"]],
        )
        eta8 = next(item for item in macros if item["id"] == "macro.eta8-target-pair")
        self.assertEqual(eta8["observed_charged_cost_e"], 1)
        self.assertEqual(
            eta8["output_symbols"], ["period.eta0_8", "period.eta4_8"]
        )


if __name__ == "__main__":
    unittest.main()
