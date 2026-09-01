"""M257-8 完整交点删二候选前沿测试。"""

from __future__ import annotations

import json
import unittest
from math import comb

import jsonschema

from build_69e_full_point_candidate_frontier import OUTPUT_PATH, ROOT, build_report


class Regular257FullPointCandidateFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_deterministic_report(self) -> None:
        schema = json.loads(
            (ROOT / "full-point-candidate-frontier.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_complete_removed_pair_inventory(self) -> None:
        trials = self.committed["trials"]
        self.assertEqual(len(trials), comb(69, 2))
        self.assertEqual(
            len({tuple(trial["removed"]) for trial in trials}),
            len(trials),
        )
        self.assertTrue(
            all(not trial["target_reached_before_candidate"] for trial in trials)
        )

    def test_definition_bounds_follow_available_exact_points(self) -> None:
        for trial in self.committed["trials"]:
            count = trial["available_exact_coordinate_points"]
            self.assertEqual(trial["line_definition_upper_bound"], comb(count, 2))
            self.assertEqual(
                trial["circle_definition_upper_bound"],
                count * (count - 1),
            )

    def test_maximum_frontier_is_final_two_moves(self) -> None:
        best = self.committed["summary"]["maximum_frontier_trials"][0]
        self.assertEqual(best["removed"], ["BG0", "target_transfer"])
        self.assertEqual(best["removed_e_moves"], [68, 69])
        self.assertEqual(best["available_paid_drawables"], 67)
        self.assertEqual(best["stalled_selected_drawables"], 0)
        self.assertEqual(best["available_points"], 2103)
        self.assertEqual(best["available_exact_coordinate_points"], 1759)
        self.assertEqual(best["available_target_circle_points"], 115)


if __name__ == "__main__":
    unittest.main()
