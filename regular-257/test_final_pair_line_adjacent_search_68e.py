"""M257-8 最后一条直线邻接既有目标圆点搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest
from itertools import combinations

import jsonschema

from final_pair_line_adjacent_search import (
    ORDER_COSINE,
    ORDER_SINE,
    ball_carrier,
    ball_carrier_may_contain_initial_neighbor,
    ball_carriers_may_have_adjacent_points,
    exact_carrier_contains_initial_neighbor,
    exact_carriers_have_adjacent_points,
)
from run_68e_final_pair_line_adjacent_search import (
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    ROOT,
    _pair_at,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257FinalPairLineAdjacentSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "final-pair-line-adjacent-search.schema.json").read_text(
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

    def test_complete_definition_and_relation_accounting(self) -> None:
        universe = self.report["universe"]
        search = self.report["search"]
        relation_count = 2 + 2 * universe["existing_target_carriers"]
        self.assertEqual(
            search["ball_relation_checks"],
            search["definitions_tested"] * relation_count,
        )
        self.assertEqual(
            search["definitions_tested"],
            search["ball_excluded_definitions"] + search["exact_checks"],
        )
        self.assertEqual(search["solutions"], [])

    def test_pair_random_access_matches_combinations(self) -> None:
        pairs = list(combinations(range(25), 2))
        self.assertEqual(
            [_pair_at(index, 25) for index in range(len(pairs))],
            pairs,
        )

    def test_initial_point_neighbor_positive_case(self) -> None:
        destination = (-ORDER_SINE, ORDER_COSINE, -2)
        self.assertTrue(
            ball_carrier_may_contain_initial_neighbor(
                ball_carrier(destination),
                1,
            )
        )
        self.assertTrue(exact_carrier_contains_initial_neighbor(destination, 1))

    def test_rotated_carrier_coincident_positive_case(self) -> None:
        source = (1, 0, -2)
        destination = (ORDER_COSINE, ORDER_SINE, -2)
        self.assertTrue(
            ball_carriers_may_have_adjacent_points(
                ball_carrier(source),
                ball_carrier(destination),
                1,
            )
        )
        self.assertTrue(exact_carriers_have_adjacent_points(source, destination, 1))

    def test_non_adjacent_carrier_negative_case(self) -> None:
        source = (1, 0, -2)
        destination = (1, 0, 0)
        self.assertFalse(
            ball_carriers_may_have_adjacent_points(
                ball_carrier(source),
                ball_carrier(destination),
                1,
            )
        )
        self.assertFalse(exact_carriers_have_adjacent_points(source, destination, 1))


if __name__ == "__main__":
    unittest.main()
