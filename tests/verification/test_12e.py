from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from euclid_min.formats import construction_sha256
from euclid_min.verifier import verify_files


ROOT = Path(__file__).resolve().parents[2]
CERTIFICATE = ROOT / "qq-ggb/construction-12e-011.json"
PROFILE = ROOT / "profiles/regular-17-e-fixed-v1.yaml"


class TwelveMoveCertificateTests(unittest.TestCase):
    def test_certificate_reaches_both_targets_at_twelve_moves(self):
        report = verify_files(CERTIFICATE, PROFILE)
        self.assertTrue(report.valid, report.data)
        self.assertEqual(report.data["draw_operations"], {"lines": 3, "circles": 9, "total": 12})
        self.assertEqual(report.data["first_target_e_move"], 12)
        self.assertEqual(report.data["duplicate_draws"], 0)
        self.assertEqual(report.data["targets"], ["B_plus", "B_minus"])
        self.assertEqual(report.data["supported_claim"], "verified_construction")

    def verify_changed(self, data):
        data["integrity"]["construction_sha256"] = construction_sha256(data["construction"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return verify_files(path, PROFILE)

    def test_original_nonadjacent_branch_is_rejected(self):
        certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
        for entry in certificate["construction"]["program"]:
            if entry["id"] in {"ggb_K", "ggb_P"}:
                entry["index"] = 1 if entry["id"] == "ggb_K" else 0
        report = self.verify_changed(certificate)
        self.assertFalse(report.valid)
        self.assertEqual(report.data["error"]["code"], "target_not_reached")

    def test_claiming_eleven_moves_is_rejected(self):
        certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
        certificate["assertions"]["score"]["e_move"] = 11
        report = self.verify_changed(certificate)
        self.assertFalse(report.valid)
        self.assertEqual(report.data["error"]["code"], "score_assertion_mismatch")
