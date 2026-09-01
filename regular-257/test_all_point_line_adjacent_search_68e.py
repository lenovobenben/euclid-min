"""M257-8 最大前沿全部点直线邻接搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from run_68e_all_point_line_adjacent_search import (
    CERTIFICATE_PATH,
    FRONTIER_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    POINT_AUDIT_PATH,
    ROOT,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257AllPointLineAdjacentSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "all-point-line-adjacent-search.schema.json").read_text(
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

    def test_complete_relation_accounting(self) -> None:
        universe = self.report["universe"]
        search = self.report["search"]
        relations_per_definition = 2 + 2 * universe["existing_target_carriers"]
        self.assertEqual(
            search["ball_relation_checks"],
            search["definitions_tested"] * relations_per_definition,
        )
        self.assertEqual(search["definitions_tested"], universe["line_definitions"])
        self.assertEqual(search["ball_excluded_definitions"], search["definitions_tested"])
        self.assertEqual(search["unresolved_definitions"], [])


if __name__ == "__main__":
    unittest.main()
