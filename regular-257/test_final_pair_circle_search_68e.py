"""M257-8 删除最后两步后的单圆候选搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from cyclotomic_replay import ORDER_FIELD
from final_pair_circle_search import (
    ball_circle_self_chord_may_hit,
    exact_circle_self_chord_hit,
)
from final_pair_line_adjacent_search import ball_carrier
from run_68e_final_pair_circle_search import (
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    ROOT,
    _ordered_pair_at,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257FinalPairCircleSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "final-pair-circle-search.schema.json").read_text(
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

    def test_complete_definition_accounting(self) -> None:
        universe = self.report["universe"]
        search = self.report["search"]
        point_count = universe["available_exact_coordinate_points"]
        self.assertEqual(universe["circle_definitions"], point_count * (point_count - 1))
        self.assertEqual(
            search["definitions_tested"],
            search["ball_excluded_definitions"] + search["exact_checks"],
        )
        normal_relation_count = 3 + 2 * universe["existing_target_carriers"]
        self.assertEqual(
            search["ball_relation_checks"],
            search["ball_excluded_definitions"] * normal_relation_count
            + search["exact_checks"],
        )
        self.assertEqual(search["exact_checks"], 6)
        self.assertEqual(search["solutions"], [])

    def test_ordered_pair_random_access(self) -> None:
        pairs = [(center, through) for center in range(20) for through in range(20) if center != through]
        self.assertEqual(
            [_ordered_pair_at(index, 20) for index in range(len(pairs))],
            pairs,
        )

    def test_exact_target_common_chord_positive_case(self) -> None:
        zeta = ORDER_FIELD.gen(514)
        x = 2 * ((zeta + zeta**-1) / 2)
        carrier = (-2, 0, 2 * x)
        self.assertTrue(ball_circle_self_chord_may_hit(ball_carrier(carrier)))
        self.assertTrue(exact_circle_self_chord_hit(carrier))

    def test_redrawing_target_circle_is_rejected_exactly(self) -> None:
        carrier = (0, 0, 0)
        self.assertTrue(ball_circle_self_chord_may_hit(ball_carrier(carrier)))
        self.assertFalse(exact_circle_self_chord_hit(carrier))


if __name__ == "__main__":
    unittest.main()
