"""正 257 边形 69E 完整有限实交点闭包测试。"""

from __future__ import annotations

import json
import unittest

import jsonschema

from build_69e_full_intersection_closure import OUTPUT_PATH, ROOT, build_report


class Regular257FullIntersectionClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_committed_report(self) -> None:
        schema = json.loads(
            (ROOT / "full-intersection-closure.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_complete_arrangement_counts(self) -> None:
        summary = self.committed["summary"]
        self.assertEqual(summary["drawable_pairs"], 2415)
        self.assertEqual(summary["raw_intersection_count"], 2706)
        self.assertEqual(summary["unique_finite_real_points"], 2287)
        self.assertEqual(summary["named_points"], 83)
        self.assertEqual(summary["unnamed_points"], 2204)
        points = self.committed["arrangement"]["points"]
        self.assertEqual(
            sum(point["producer_pair_count"] for point in points),
            summary["raw_intersection_count"],
        )

    def test_all_existing_object_definitions_are_available(self) -> None:
        drawables = self.committed["arrangement"]["drawables"]
        self.assertEqual(len(drawables), 69)
        self.assertEqual(
            sum(
                drawable["condition"]["definition_count"]
                for drawable in drawables
            ),
            133558,
        )
        for drawable in drawables:
            first, second = drawable["declared_definition"]
            condition = drawable["condition"]
            if condition["kind"] == "two_incident_points":
                self.assertIn(first, condition["incident_points"])
                self.assertIn(second, condition["incident_points"])
            else:
                self.assertIn(first, condition["center_points"])
                self.assertIn(second, condition["through_points"])

    def test_single_deletion_exhaustion_proves_fixed_universe_minimum(self) -> None:
        trials = self.committed["single_deletion_trials"]
        self.assertEqual(len(trials), 69)
        self.assertTrue(all(not trial["target_reached"] for trial in trials))
        result = self.committed["irreducibility_result"]
        self.assertTrue(result["all_paid_draws_individually_necessary"])
        self.assertEqual(result["removable_paid_draws"], [])
        self.assertEqual(
            result["minimum_required_paid_draws_within_fixed_object_universe"],
            69,
        )
        self.assertEqual(
            [trial["removed"] for trial in trials],
            result["required_paid_draws"],
        )


if __name__ == "__main__":
    unittest.main()
