"""M257-8 删除最后两步后的目标弦直线搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from cyclotomic_replay import ORDER_FIELD, Point
from final_pair_line_chord_search import (
    ball_line_chord_may_hit,
    deserialize_ball_point,
    exact_line_chord_hit,
    real_ball_point,
    serialize_ball_point,
)
from run_68e_final_pair_line_chord_search import (
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    ROOT,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257FinalPairLineChordSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "final-pair-line-chord-search.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.report)
        source = self.report["source"]
        self.assertEqual(source["certificate_sha256"], sha256_file(CERTIFICATE_PATH))
        self.assertEqual(
            source["full_intersection_closure_report_sha256"],
            sha256_file(FULL_CLOSURE_PATH),
        )
        self.assertEqual(
            source["candidate_frontier_report_sha256"],
            sha256_file(FRONTIER_PATH),
        )

    def test_exhaustive_definition_accounting(self) -> None:
        universe = self.report["universe"]
        search = self.report["search"]
        self.assertEqual(
            universe["line_definitions"],
            universe["available_exact_coordinate_points"]
            * (universe["available_exact_coordinate_points"] - 1)
            // 2,
        )
        self.assertEqual(
            search["definitions_tested"],
            search["ball_excluded_definitions"] + search["exact_checks"],
        )
        self.assertEqual(search["solutions"], [])

    def test_filter_preserves_an_exact_target_chord(self) -> None:
        zeta = ORDER_FIELD.gen(514)
        half_angle_cosine = (zeta + zeta**-1) / 2
        x = 2 * half_angle_cosine
        first = Point(x, -1)
        second = Point(x, 0)
        first_ball = deserialize_ball_point(
            serialize_ball_point(real_ball_point(first))
        )
        second_ball = deserialize_ball_point(
            serialize_ball_point(real_ball_point(second))
        )
        self.assertTrue(ball_line_chord_may_hit(first_ball, second_ball))
        self.assertTrue(exact_line_chord_hit(first, second))

    def test_filter_rejects_a_non_target_chord(self) -> None:
        first = Point(1, -1)
        second = Point(1, 0)
        self.assertFalse(
            ball_line_chord_may_hit(
                real_ball_point(first),
                real_ball_point(second),
            )
        )
        self.assertFalse(exact_line_chord_hit(first, second))


if __name__ == "__main__":
    unittest.main()
