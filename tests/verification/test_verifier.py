from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from euclid_min.canonical_json import sha256_hex
from euclid_min.formats import construction_sha256, load_certificate, load_profile
from euclid_min.replay import ReplayResult
from euclid_min.state import GeometryState
from euclid_min.target import TargetName
from euclid_min.verifier import verify_files, verify_loaded


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
CERTIFICATE_PATH = (
    REPOSITORY_ROOT / "tests" / "fixtures" / "certificates" / "not-target.json"
)
REPORT_SCHEMA_PATH = (
    REPOSITORY_ROOT / "schemas" / "verification-report-v1.schema.json"
)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))

    def test_structurally_valid_non_target_certificate_has_stable_failure(self):
        report = verify_files(CERTIFICATE_PATH, PROFILE_PATH)
        self.assertFalse(report.valid)
        self.assertEqual(report.data["error"]["code"], "target_not_reached")
        self.assertEqual(report.data["error"]["details"]["e_move"], 2)
        self.assertEqual(
            report.data["construction_sha256"],
            self.certificate["integrity"]["construction_sha256"],
        )
        self._assert_report_schema(report.data)

    def test_profile_hash_mismatch_precedes_replay(self):
        data = copy.deepcopy(self.certificate)
        data["profile"]["sha256"] = "0" * 64
        report = self._verify_temporary(data)
        self.assertEqual(report.data["error"]["code"], "profile_hash_mismatch")

    def test_construction_hash_mismatch_is_rejected(self):
        data = copy.deepcopy(self.certificate)
        data["construction"]["title"] = "changed"
        report = self._verify_temporary(data)
        self.assertEqual(
            report.data["error"]["code"],
            "construction_hash_mismatch",
        )

    def test_score_assertion_is_recomputed(self):
        data = copy.deepcopy(self.certificate)
        data["assertions"]["score"]["e_move"] = 1
        report = self._verify_temporary(data)
        self.assertEqual(report.data["error"]["code"], "score_assertion_mismatch")
        self.assertEqual(report.data["error"]["details"]["actual"], 2)

    def test_program_error_is_reported_after_hash_is_updated(self):
        data = copy.deepcopy(self.certificate)
        data["construction"]["program"][0]["through"][1] = "missing"
        data["integrity"]["construction_sha256"] = sha256_hex(
            data["construction"]
        )
        report = self._verify_temporary(data)
        self.assertEqual(report.data["error"]["code"], "unknown_reference")
        self.assertEqual(report.data["error"]["program_index"], 0)

    def test_schema_error_is_returned_as_report(self):
        data = copy.deepcopy(self.certificate)
        data["assertions"]["score"]["e_move"] = 0
        report = self._verify_temporary(data)
        self.assertEqual(report.data["error"]["code"], "schema_invalid")
        self.assertIn("certificate_sha256", report.data)
        self._assert_report_schema(report.data)

    def test_success_report_path_and_claim_ceiling(self):
        certificate = load_certificate(CERTIFICATE_PATH)
        profile = load_profile(PROFILE_PATH)
        replay = ReplayResult(
            state=GeometryState.fixed_initial(),
            names={},
            line_draws=1,
            circle_draws=1,
            duplicate_draws=0,
            targets=(TargetName.B_PLUS,),
            first_target_program_index=2,
            first_target_e_move=2,
        )
        with patch("euclid_min.verifier.ProgramReplayer") as replayer_class:
            replayer_class.return_value.replay.return_value = replay
            report = verify_loaded(certificate, profile)

        self.assertTrue(report.valid)
        self.assertEqual(report.data["score"]["e_move"], 2)
        self.assertEqual(report.data["targets"], ["B_plus"])
        self.assertEqual(
            report.data["construction_sha256"],
            construction_sha256(certificate.data["construction"]),
        )
        self.assertEqual(report.data["supported_claim"], "verified_construction")
        self._assert_report_schema(report.data)

    def _verify_temporary(self, data):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "certificate.json"
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return verify_files(path, PROFILE_PATH)

    def _assert_report_schema(self, report):
        schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)


if __name__ == "__main__":
    unittest.main()
