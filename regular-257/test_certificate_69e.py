"""正 257 边形 69E JSON 证书回归测试。"""

from __future__ import annotations

import json
import unittest

import jsonschema

from verify_69e_certificate import (
    CERTIFICATE_PATH,
    CERTIFICATE_SCHEMA_PATH,
    ROOT,
    verify_certificate,
)


class Regular257CertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.certificate = json.loads(
            CERTIFICATE_PATH.read_text(encoding="utf-8")
        )
        cls.report = verify_certificate()

    def test_certificate_schema_and_program_shape(self) -> None:
        schema = json.loads(
            CERTIFICATE_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.certificate)
        self.assertEqual(len(self.certificate["construction"]["program"]), 150)

    def test_exact_replay_report(self) -> None:
        self.assertTrue(self.report["valid"])
        self.assertEqual(self.report["proof_hints_verified"], 81)
        self.assertEqual(
            self.report["draws"],
            {
                "lines": 65,
                "circles": 4,
                "duplicates": 0,
            },
        )
        self.assertEqual(self.report["score"]["e_move"], 69)
        self.assertEqual(
            self.report["target_witnesses"],
            [["G", "W2_minus"], ["G", "W2_plus"]],
        )
        self.assertEqual(self.report["first_bound_target_e_move"], 69)
        self.assertEqual(
            self.report["automatic_closure_target_audit"],
            {
                "status": "complete",
                "method": "exact_rotated_chord_carriers",
                "first_target_e_move": 69,
            },
        )
        self.assertEqual(
            {item["source_object"] for item in self.report["first_target_sources"]},
            {"BE", "b", "GDa", "GDb"},
        )

    def test_committed_report_matches_fresh_replay(self) -> None:
        committed = json.loads(
            (ROOT / "verification-69e.json").read_text(encoding="utf-8")
        )
        schema = json.loads(
            (ROOT / "verification.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(committed)
        self.assertEqual(committed, self.report)


if __name__ == "__main__":
    unittest.main()
