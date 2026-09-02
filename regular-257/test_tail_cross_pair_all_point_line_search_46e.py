"""46E 完整点闭包跨尾部一笔直线搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_46e_tail_cross_pair_all_point_line_search import (
    CERTIFICATE_PATH,
    FULL_CLOSURE_PATH,
    GA_IR_PATH,
    NAMED_SEARCH_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257TailCrossPairAllPointLineSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (ROOT / "tail-cross-pair-all-point-line-search.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_source_hashes(self) -> None:
        source = self.committed["source"]
        self.assertEqual(source["certificate_sha256"], sha256_file(CERTIFICATE_PATH))
        self.assertEqual(
            source["full_intersection_closure_report_sha256"],
            sha256_file(FULL_CLOSURE_PATH),
        )
        self.assertEqual(source["geometry_algebra_ir_sha256"], sha256_file(GA_IR_PATH))
        self.assertEqual(
            source["named_prefix_search_sha256"],
            sha256_file(NAMED_SEARCH_PATH),
        )

    def test_complete_point_line_incidence_audit(self) -> None:
        universe = self.committed["universe"]
        summary = self.committed["summary"]
        self.assertEqual(universe["available_points"], 989)
        self.assertEqual(universe["exact_coordinate_points"], 763)
        self.assertEqual(universe["abstract_residual_points"], 226)
        self.assertEqual(len(universe["abstract_producer_groups"]), 120)
        self.assertEqual(universe["ambiguous_point_pairs"], [])
        self.assertEqual(summary["cross_root_lines"], 36)
        self.assertEqual(summary["strict_ball_incidence_checks"], 36 * 989)
        self.assertEqual(summary["strict_ball_survivors"], 0)
        self.assertEqual(summary["exact_coordinate_fallbacks"], 0)
        self.assertEqual(summary["abstract_incidence_fallbacks"], 0)

    def test_no_available_point_lies_on_a_cross_root_line(self) -> None:
        for result in self.committed["results"]:
            self.assertEqual(result["incident_points"], [])
            self.assertEqual(result["definition_count"], 0)
            self.assertEqual(result["new_definition_count"], 0)
        self.assertEqual(self.committed["summary"]["definitions_found"], 0)
        self.assertEqual(self.committed["summary"]["new_definitions_found"], 0)
        self.assertEqual(self.committed["candidate_root_pairs"], [])
        self.assertEqual(
            self.committed["conclusion"]["status"],
            "exhausted_no_candidate",
        )


if __name__ == "__main__":
    unittest.main()
