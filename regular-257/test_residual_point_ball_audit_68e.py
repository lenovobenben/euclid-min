"""M257-8 最大前沿抽象残余点严格实球审计测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_68e_residual_point_ball_audit import (
    CACHE_PATH,
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    ROOT,
)
from cyclotomic_replay import Circle, Point
from residual_point_ball_audit import (
    BALL_PRECISION,
    balls_may_overlap,
    circle_circle_intersection_balls,
    line_circle_intersection_balls,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257ResidualPointBallAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "residual-point-ball-audit.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.report)
        source = self.report["source"]
        expected = {
            "certificate_sha256": CERTIFICATE_PATH,
            "full_intersection_closure_report_sha256": FULL_CLOSURE_PATH,
            "candidate_frontier_report_sha256": FRONTIER_PATH,
        }
        for key, path in expected.items():
            self.assertEqual(source[key], sha256_file(path))

    def test_cache_covers_every_available_point(self) -> None:
        self.assertEqual(self.cache["source"], self.report["source"])
        self.assertEqual(self.cache["precision_bits"], BALL_PRECISION)
        self.assertEqual(
            len(self.cache["point_ids"]),
            self.report["universe"]["available_points"],
        )
        self.assertEqual(len(self.cache["balls"]), len(self.cache["point_ids"]))
        self.assertEqual(len(set(self.cache["point_ids"])), len(self.cache["point_ids"]))

    def test_line_circle_secant_and_tangent(self) -> None:
        circle = Circle(Point(0, 0), 1)
        secant = line_circle_intersection_balls((1, 0, 0), circle)
        self.assertEqual(len(secant), 2)
        self.assertFalse(balls_may_overlap(secant[0], secant[1]))
        for x, y in secant:
            self.assertTrue(x.contains_zero())
            self.assertTrue((x * x + y * y - 1).contains_zero())

        tangent = line_circle_intersection_balls((1, 0, -1), circle)
        self.assertEqual(len(tangent), 1)
        x, y = tangent[0]
        self.assertTrue((x - 1).contains_zero())
        self.assertTrue(y.contains_zero())

    def test_circle_circle_secant(self) -> None:
        first = Circle(Point(0, 0), 1)
        second = Circle(Point(1, 0), 1)
        roots = circle_circle_intersection_balls(first, second)
        self.assertEqual(len(roots), 2)
        self.assertFalse(balls_may_overlap(roots[0], roots[1]))
        for x, y in roots:
            self.assertTrue((x * x + y * y - 1).contains_zero())
            self.assertTrue(((x - 1) * (x - 1) + y * y - 1).contains_zero())


if __name__ == "__main__":
    unittest.main()
