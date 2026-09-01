"""46E 完整点闭包跨尾部一笔圆搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_46e_tail_cross_pair_all_point_circle_search import (
    ALL_POINT_LINE_PATH,
    CERTIFICATE_PATH,
    FULL_CLOSURE_PATH,
    GA_IR_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257TailCrossPairAllPointCircleSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (ROOT / "tail-cross-pair-all-point-circle-search.schema.json").read_text(
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
            source["all_point_line_search_sha256"],
            sha256_file(ALL_POINT_LINE_PATH),
        )

    def test_complete_point_center_incidence_audit(self) -> None:
        universe = self.committed["universe"]
        summary = self.committed["summary"]
        self.assertEqual(universe["available_points"], 989)
        self.assertEqual(universe["exact_coordinate_points"], 763)
        self.assertEqual(universe["abstract_residual_points"], 226)
        self.assertEqual(universe["ambiguous_point_pairs"], [])
        self.assertEqual(summary["cross_root_pairs"], 36)
        self.assertEqual(summary["strict_ball_center_checks"], 36 * 989)
        self.assertEqual(summary["strict_ball_survivors"], 36)
        self.assertEqual(summary["exact_center_fallbacks"], 36)
        self.assertEqual(summary["abstract_center_fallbacks"], 0)
        self.assertEqual(summary["center_incidences"], 36)

    def test_only_existing_encoding_circle_survives(self) -> None:
        for result in self.committed["results"]:
            self.assertEqual(result["center_points"], ["A"])
            self.assertEqual(result["exact_center_points"], ["A"])
            self.assertEqual(result["abstract_center_points"], [])
            self.assertEqual(
                result["existing_circle_centers"],
                [{"center": "A", "existing_drawable_references": ["c"]}],
            )
            self.assertEqual(result["new_exact_center_points"], [])
            self.assertEqual(result["new_abstract_center_points"], [])
            self.assertEqual(result["unresolved_new_center_count"], 0)

        summary = self.committed["summary"]
        self.assertEqual(summary["existing_circle_center_incidences"], 36)
        self.assertEqual(summary["new_exact_center_incidences"], 0)
        self.assertEqual(summary["new_abstract_center_incidences"], 0)
        self.assertEqual(summary["root_pairs_requiring_through_point_audit"], 0)
        self.assertEqual(self.committed["candidate_root_pairs"], [])
        self.assertEqual(
            self.committed["conclusion"]["status"],
            "exhausted_no_new_circle_center",
        )


if __name__ == "__main__":
    unittest.main()
