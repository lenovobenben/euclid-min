"""非锚定正 257 边形 profile 与目标语义测试。"""

from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import yaml
from sage.all import UniversalCyclotomicField

from euclid_min.canonical_json import sha256_hex
from target import (
    InvalidPrimitiveRootError,
    adjacent_chord_squared,
    first_target_pair,
    is_target_pair,
)


ROOT = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "profile.yaml"
SCHEMA_PATH = ROOT / "profile.schema.json"
HASH_PATH = ROOT / "profile.sha256"


@dataclass(frozen=True)
class ExactPoint:
    x: object
    y: object


@dataclass(frozen=True)
class ExactCircle:
    center: ExactPoint
    radius_squared: object

    def contains(self, point: ExactPoint) -> bool:
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        return dx * dx + dy * dy == self.radius_squared


class Regular257ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        field = UniversalCyclotomicField()
        cls.zeta = field.gen(257)
        cls.imaginary_unit = field.gen(4)
        cls.center = ExactPoint(field(0), field(-1))
        cls.initial = ExactPoint(field(0), field(1))
        cls.circle = ExactCircle(cls.center, field(4))

    def test_profile_schema_and_digest(self) -> None:
        profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(profile)

        expected = HASH_PATH.read_text(encoding="utf-8").strip()
        self.assertEqual(sha256_hex(profile), expected)

    def test_initial_state_does_not_already_reach_target(self) -> None:
        self.assertIsNone(
            first_target_pair(
                self.circle,
                (self.center, self.initial),
                self.zeta,
            )
        )

    def test_exact_adjacent_pair_in_both_orientations(self) -> None:
        cosine = (self.zeta + self.zeta**-1) / 2
        sine = (self.zeta - self.zeta**-1) / (2 * self.imaginary_unit)
        right = ExactPoint(2, -1)
        upper = ExactPoint(2 * cosine, -1 + 2 * sine)
        lower = ExactPoint(2 * cosine, -1 - 2 * sine)

        self.assertEqual(
            adjacent_chord_squared(self.circle, self.zeta),
            8 * (1 - cosine),
        )
        self.assertTrue(is_target_pair(self.circle, right, upper, self.zeta))
        self.assertTrue(is_target_pair(self.circle, right, lower, self.zeta))
        self.assertFalse(
            is_target_pair(self.circle, self.initial, upper, self.zeta)
        )
        self.assertEqual(
            first_target_pair(
                self.circle,
                (self.center, self.initial, right, upper),
                self.zeta,
            ),
            (right, upper),
        )

    def test_points_must_lie_on_given_circle(self) -> None:
        right = ExactPoint(2, -1)
        off_circle = ExactPoint(2, 0)
        self.assertFalse(
            is_target_pair(self.circle, right, off_circle, self.zeta)
        )

    def test_rejects_invalid_primitive_root(self) -> None:
        with self.assertRaises(InvalidPrimitiveRootError):
            adjacent_chord_squared(self.circle, self.zeta**2 + 1)


if __name__ == "__main__":
    unittest.main()
