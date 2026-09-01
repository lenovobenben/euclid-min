"""正 257 边形 69E 精确语义依赖超图测试。"""

from __future__ import annotations

import json
import unittest

import jsonschema

from build_69e_semantic_dependencies import OUTPUT_PATH, ROOT, build_report


class Regular257SemanticDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_committed_report(self) -> None:
        schema = json.loads(
            (ROOT / "semantic-dependencies.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_causal_producers_are_unique(self) -> None:
        points = self.committed["hypergraph"]["points"]
        self.assertEqual(len(points), 81)
        self.assertTrue(
            all(len(point["producers_at_declared_binding"]) == 1 for point in points)
        )
        self.assertTrue(
            all(
                len(point["producers_before_first_paid_use"]) == 1
                for point in points
            )
        )
        self.assertEqual(
            sum(len(point["producers_in_final_state"]) for point in points),
            401,
        )
        self.assertEqual(
            sum(len(point["producers_in_final_state"]) > 1 for point in points),
            78,
        )

    def test_all_named_object_definitions_are_enumerated(self) -> None:
        drawables = self.committed["hypergraph"]["drawables"]
        self.assertEqual(len(drawables), 69)
        self.assertEqual(
            sum(
                len(drawable["exact_named_point_definitions"])
                for drawable in drawables
            ),
            694,
        )
        self.assertTrue(
            all(
                len(drawable["exact_named_point_definitions"]) > 1
                for drawable in drawables
            )
        )

    def test_single_deletion_exhaustion_proves_relative_minimum(self) -> None:
        trials = self.committed["single_deletion_trials"]
        self.assertEqual(len(trials), 69)
        self.assertTrue(all(not trial["target_reached"] for trial in trials))
        self.assertEqual(
            [trial["removed"] for trial in trials],
            self.committed["irreducibility_result"]["required_paid_draws"],
        )
        result = self.committed["irreducibility_result"]
        self.assertTrue(result["all_paid_draws_individually_necessary"])
        self.assertEqual(result["removable_paid_draws"], [])
        self.assertEqual(result["minimum_required_paid_draws_within_universe"], 69)


if __name__ == "__main__":
    unittest.main()
