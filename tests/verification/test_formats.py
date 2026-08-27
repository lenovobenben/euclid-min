from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from euclid_min.errors import VerificationError
from euclid_min.formats import load_certificate, load_profile


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
CERTIFICATE_PATH = (
    REPOSITORY_ROOT / "tests" / "fixtures" / "certificates" / "not-target.json"
)


class FormatLoadingTests(unittest.TestCase):
    def test_profile_and_certificate_pass_structural_validation(self):
        profile = load_profile(PROFILE_PATH)
        certificate = load_certificate(CERTIFICATE_PATH)
        self.assertEqual(profile.data["id"], "regular-17-e-fixed-v1")
        self.assertEqual(
            profile.sha256,
            "bb0a4ea904e60fb688da15558fa8f09982d4a7eee3cd8efee32ae9cb61079014",
        )
        self.assertEqual(certificate.data["construction"]["id"], "not-target")

    def test_duplicate_json_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "duplicate.json"
            path.write_text('{"schema": 1, "schema": 2}', encoding="utf-8")
            with self.assertRaises(VerificationError) as caught:
                load_certificate(path)
        self.assertEqual(caught.exception.code, "certificate_json_invalid")

    def test_duplicate_yaml_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "duplicate.yaml"
            path.write_text("schema: first\nschema: second\n", encoding="utf-8")
            with self.assertRaises(VerificationError) as caught:
                load_profile(path)
        self.assertEqual(caught.exception.code, "profile_yaml_invalid")

    def test_certificate_schema_failure_is_stable(self):
        data = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
        data["assertions"]["score"]["e_move"] = 0
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(VerificationError) as caught:
                load_certificate(path)
        self.assertEqual(caught.exception.code, "schema_invalid")
        self.assertEqual(
            caught.exception.details["instance_path"],
            "assertions/score/e_move",
        )


if __name__ == "__main__":
    unittest.main()
