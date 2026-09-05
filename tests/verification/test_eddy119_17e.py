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
    / "eddy119-2026-adapted-17e"
)
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
REPORT_SCHEMA_PATH = (
    REPOSITORY_ROOT / "schemas" / "verification-report-v1.schema.json"
)


class Eddy119AdaptedTests(unittest.TestCase):
    def test_adaptation_is_a_verified_17_e_upper_bound(self):
        report = verify_files(BASELINE_DIRECTORY / "construction.json", PROFILE_PATH)

        self.assertTrue(report.valid)
        self.assertEqual(report.data["score"], {"metric": "e_move", "e_move": 17})
        self.assertEqual(
            report.data["draw_operations"],
            {"lines": 7, "circles": 10, "total": 17},
        )
        self.assertEqual(report.data["targets"], ["B_plus"])
        self.assertEqual(report.data["first_target_e_move"], 17)
        self.assertEqual(report.data["duplicate_draws"], 0)

        schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(report.data)

    def test_independent_radical_report_passed_every_check(self):
        report = json.loads(
            (BASELINE_DIRECTORY / "independent_radical_report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(report["all_checks_passed"])
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["adapted_draw_count"], {
            "lines": 7,
            "circles": 10,
            "E": 17,
        })


if __name__ == "__main__":
    unittest.main()
