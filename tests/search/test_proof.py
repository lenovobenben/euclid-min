from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator
from sage.all import AA

from euclid_min.errors import VerificationError
from euclid_min.geometry import Point
from euclid_min.search.model import PointGoal
from euclid_min.search.proof import (
    DEFAULT_PROOF_SCHEMA,
    DEFAULT_PROOF_V2_SCHEMA,
    build_bounded_proof,
    check_bounded_proof,
    enumerate_bounded_proof,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
LEGACY_PROOF_PATH = (
    REPOSITORY_ROOT / "proofs" / "regular-17-through-4e.json"
)
PUBLISHED_PROOF_PATH = (
    REPOSITORY_ROOT / "proofs" / "regular-17-through-5e.json"
)


class ProofEnumerationTests(unittest.TestCase):
    def test_layered_enumeration_proves_midpoint_absent_through_two_moves(self):
        midpoint = PointGoal(Point(AA(1) / 2, 0))
        optimized = enumerate_bounded_proof(midpoint, max_score=2)
        reference = enumerate_bounded_proof(midpoint, max_score=2, reference=True)

        self.assertEqual(optimized.status, "exhausted")
        self.assertEqual(optimized.minimum_score, None)
        self.assertEqual(optimized.layers, reference.layers)
        self.assertEqual(optimized.accepted_states, reference.accepted_states)

    def test_layered_enumeration_reports_exact_minimum_when_found(self):
        equilateral = PointGoal(Point(AA(1) / 2, AA(3).sqrt() / 2))
        result = enumerate_bounded_proof(equilateral, max_score=1)

        self.assertEqual(result.status, "found")
        self.assertEqual(result.minimum_score, 1)
        self.assertIsNotNone(result.node)
        self.assertEqual(result.layers[0].goal_states, 0)
        self.assertGreaterEqual(result.layers[1].goal_states, 1)


class BoundedProofRecordTests(unittest.TestCase):
    def test_legacy_four_move_record_remains_v1_schema_valid(self):
        proof = json.loads(LEGACY_PROOF_PATH.read_text(encoding="utf-8"))
        schema = json.loads(DEFAULT_PROOF_SCHEMA.read_text(encoding="utf-8"))

        Draft202012Validator(schema).validate(proof)
        self.assertEqual(proof["bound"]["max_score"], 4)

    def test_published_five_move_proof_replays_with_reference_checker(self):
        proof = json.loads(PUBLISHED_PROOF_PATH.read_text(encoding="utf-8"))
        schema = json.loads(DEFAULT_PROOF_V2_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(proof)

        checked = check_bounded_proof(
            PUBLISHED_PROOF_PATH,
            profile_path=PROFILE_PATH,
            workers=8,
        )

        self.assertTrue(checked["valid"])
        self.assertEqual(checked["bound"]["max_score"], 5)
        self.assertEqual(checked["result"]["status"], "exhausted")
        self.assertEqual(
            checked["checker"],
            "linear_exact_forward_and_object_incidence_reference_replay",
        )

    def test_record_matches_schema_and_reference_replay(self):
        proof = build_bounded_proof(profile_path=PROFILE_PATH, max_score=1)
        schema = json.loads(DEFAULT_PROOF_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(proof)

        self.assertEqual(proof["result"]["status"], "exhausted")
        self.assertFalse(proof["proof_mode"]["heuristic_pruning"])
        self.assertIsNone(proof["proof_mode"]["state_limit"])
        self.assertFalse(proof["proof_mode"]["timeouts"])
        self.assertEqual(proof["totals"]["terminal_candidates"], 0)
        self.assertGreater(
            proof["totals"]["terminal_nonmatching_pruned"],
            0,
        )

        with TemporaryDirectory() as temporary_directory:
            proof_path = Path(temporary_directory) / "proof.json"
            proof_path.write_text(
                json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            checked = check_bounded_proof(
                proof_path,
                profile_path=PROFILE_PATH,
            )

        self.assertTrue(checked["valid"])
        self.assertEqual(checked["checker"], "linear_exact_reference_replay")

    def test_reference_replay_rejects_schema_valid_tampering(self):
        proof = build_bounded_proof(profile_path=PROFILE_PATH, max_score=1)
        proof["layers"][0]["generated_candidates"] += 1

        with TemporaryDirectory() as temporary_directory:
            proof_path = Path(temporary_directory) / "tampered.json"
            proof_path.write_text(
                json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(VerificationError) as raised:
                check_bounded_proof(
                    proof_path,
                    profile_path=PROFILE_PATH,
                )

        self.assertEqual(raised.exception.code, "proof_replay_mismatch")


if __name__ == "__main__":
    unittest.main()
