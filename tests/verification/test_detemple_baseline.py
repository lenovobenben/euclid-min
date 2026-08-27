from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from euclid_min.verifier import verify_files


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIRECTORY = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-converted"
)
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
REPORT_SCHEMA_PATH = (
    REPOSITORY_ROOT / "schemas" / "verification-report-v1.schema.json"
)


class DeTempleBaselineTests(unittest.TestCase):
    def test_baseline_is_exactly_replayable(self):
        report = verify_files(
            BASELINE_DIRECTORY / "construction.json",
            PROFILE_PATH,
        )
        self.assertTrue(report.valid)
        self.assertEqual(report.data["score"], {"metric": "e_move", "e_move": 32})
        self.assertEqual(
            report.data["draw_operations"],
            {"lines": 11, "circles": 21, "total": 32},
        )
        self.assertEqual(report.data["targets"], ["B_plus", "B_minus"])
        self.assertEqual(report.data["first_target_e_move"], 32)
        self.assertEqual(report.data["closure_strategy"], "implicit_exact")

        schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(report.data)


if __name__ == "__main__":
    unittest.main()
