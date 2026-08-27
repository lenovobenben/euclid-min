from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from euclid_min.canonical_json import (
    MAX_SAFE_INTEGER,
    CanonicalizationError,
    canonicalize,
    sha256_hex,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class CanonicalJsonTests(unittest.TestCase):
    def test_primitives_and_string_escaping(self):
        self.assertEqual(
            canonicalize([None, True, False, 0, -7]),
            b"[null,true,false,0,-7]",
        )
        self.assertEqual(
            canonicalize("\b\t\n\f\r\"\\\x00\x1f"),
            b'"\\b\\t\\n\\f\\r\\"\\\\\\u0000\\u001f"',
        )

    def test_object_keys_use_utf16_order(self):
        value = {
            "€": 1,
            "\r": 1,
            "דּ": 1,
            "1": 1,
            "😀": 1,
            "\u0080": 1,
            "ö": 1,
        }
        self.assertEqual(
            canonicalize(value).decode("utf-8"),
            '{"\\r":1,"1":1,"\u0080":1,"ö":1,"€":1,"😀":1,"דּ":1}',
        )

    def test_valid_utf16_surrogate_pair_is_combined(self):
        self.assertEqual(
            canonicalize("\ud83d\ude00"),
            canonicalize("😀"),
        )

    def test_unsupported_values_are_rejected(self):
        for value in (1.5, MAX_SAFE_INTEGER + 1, {1: "not a string key"}):
            with self.subTest(value=value):
                with self.assertRaises(CanonicalizationError):
                    canonicalize(value)
        with self.assertRaises(CanonicalizationError):
            canonicalize("\ud800")

    def test_repository_profile_digest_is_stable(self):
        profile_path = (
            REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
        )
        expected_path = profile_path.with_suffix(".sha256")
        data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(sha256_hex(data), expected_path.read_text().strip())


if __name__ == "__main__":
    unittest.main()
