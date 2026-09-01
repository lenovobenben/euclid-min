"""46E 完整点闭包跨尾部两对象目标直线桥接搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter

import jsonschema

from build_46e_tail_cross_pair_two_object_line_bridge_search import (
    ALL_POINT_CIRCLE_PATH,
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


class Regular257TailCrossPairTwoObjectLineBridgeSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "tail-cross-pair-two-object-line-bridge-search.schema.json"
            ).read_text(encoding="utf-8")
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
        self.assertEqual(
            source["all_point_circle_search_sha256"],
            sha256_file(ALL_POINT_CIRCLE_PATH),
        )

    def test_complete_two_object_bridge_space(self) -> None:
        summary = self.committed["summary"]
        self.assertEqual(summary["workers"], 8)
        self.assertEqual(summary["cross_root_pairs"], 36)
        self.assertEqual(summary["center_bridge_pair_space"], 44_611_812)
        self.assertEqual(summary["strict_radius_overlap_survivors"], 136)
        self.assertEqual(summary["exact_radius_equalities"], 136)
        self.assertEqual(summary["through_point_checks"], 136 * 989)
        self.assertEqual(summary["strict_through_point_survivors"], 9_212)
        self.assertEqual(summary["exact_through_point_fallbacks"], 136)
        self.assertEqual(
            Counter(result["bridge_point_count"] for result in self.committed["results"]),
            Counter({51: 28, 49: 8}),
        )

    def test_only_existing_circles_survive(self) -> None:
        summary = self.committed["summary"]
        references = Counter()
        for result in self.committed["results"]:
            self.assertEqual(
                result["strict_radius_overlap_survivors"],
                result["exact_equidistant_center_pairs"],
            )
            self.assertEqual(
                len(result["circle_candidates"]),
                result["exact_equidistant_center_pairs"],
            )
            self.assertEqual(result["drawable_new_circle_candidates"], [])
            for candidate in result["circle_candidates"]:
                references.update(candidate["existing_drawable_references"])
                self.assertFalse(candidate["is_new_drawable"])
                self.assertFalse(candidate["is_drawable_from_46e_state"])
                self.assertTrue(candidate["available_through_points"])

        self.assertEqual(
            references,
            Counter({"c0": 36, "c": 36, "q": 36, "c_M1L1": 28}),
        )
        self.assertEqual(summary["existing_circle_equalities"], 136)
        self.assertEqual(summary["new_circle_geometries"], 0)
        self.assertEqual(summary["drawable_new_circle_candidates"], 0)
        self.assertEqual(summary["root_pairs_with_2e_bridge"], 0)
        self.assertEqual(self.committed["candidate_root_pairs"], [])
        self.assertEqual(
            self.committed["conclusion"]["status"],
            "exhausted_no_two_object_line_bridge",
        )


if __name__ == "__main__":
    unittest.main()
