"""M257-8 最大前沿全部点圆搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from run_68e_all_point_circle_search import (
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    POINT_AUDIT_PATH,
    ROOT,
    _ordered_pair_at,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257AllPointCircleSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "all-point-circle-search.schema.json").read_text(
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
            "residual_point_ball_audit_sha256": POINT_AUDIT_PATH,
        }
        for key, path in expected.items():
            self.assertEqual(source[key], sha256_file(path))

    def test_complete_definition_and_relation_accounting(self) -> None:
        universe = self.report["universe"]
        search = self.report["search"]
        point_count = universe["available_points"]
        self.assertEqual(
            universe["circle_definitions"], point_count * (point_count - 1)
        )
        self.assertEqual(
            search["definitions_tested"],
            search["ball_excluded_definitions"]
            + search["redrawn_target_circle_count"]
            + search["unresolved_count"],
        )
        normal_relations = 3 + 2 * universe["existing_target_carriers"]
        self.assertEqual(
            search["ball_relation_checks"],
            search["ball_excluded_definitions"] * normal_relations
            + search["redrawn_target_circle_count"],
        )
        self.assertEqual(search["unresolved_definitions"], [])

    def test_every_non_interval_result_is_a_target_circle_redraw(self) -> None:
        redraws = self.report["search"]["redrawn_target_circle_definitions"]
        self.assertEqual(len({item["through"] for item in redraws}), 115)
        self.assertTrue(all(item["center"] == "C" for item in redraws))

    def test_ordered_pair_random_access(self) -> None:
        pairs = [
            (center, through)
            for center in range(25)
            for through in range(25)
            if center != through
        ]
        self.assertEqual(
            [_ordered_pair_at(index, 25) for index in range(len(pairs))],
            pairs,
        )


if __name__ == "__main__":
    unittest.main()
