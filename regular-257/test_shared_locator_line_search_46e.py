"""46E 状态中共享根载线定位点的新直线搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_46e_shared_locator_line_search import (
    CERTIFICATE_PATH,
    CHORD_IR_PATH,
    FULL_CLOSURE_PATH,
    GA_IR_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257SharedLocatorLineSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema(self) -> None:
        schema = json.loads(
            (ROOT / "shared-locator-line-search.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)

    def test_source_hashes(self) -> None:
        source = self.committed["source"]
        self.assertEqual(source["certificate_sha256"], sha256_file(CERTIFICATE_PATH))
        self.assertEqual(
            source["full_intersection_closure_sha256"],
            sha256_file(FULL_CLOSURE_PATH),
        )
        self.assertEqual(
            source["geometry_algebra_ir_sha256"], sha256_file(GA_IR_PATH)
        )
        self.assertEqual(
            source["tail_quadratic_chord_ir_sha256"], sha256_file(CHORD_IR_PATH)
        )

    def test_complete_prefix_line_witness_space(self) -> None:
        summary = self.committed["summary"]
        self.assertEqual(summary["workers"], 8)
        self.assertEqual(summary["task_pairs"], 15)
        self.assertEqual(summary["bridge_pair_space"], 27_306)
        self.assertEqual(summary["coincident_bridge_pairs"], 1)
        self.assertEqual(summary["candidate_line_occurrences"], 27_305)
        self.assertEqual(summary["strict_ball_checks"], 26_394_189)
        self.assertEqual(summary["strict_ball_survivors"], 1_696)
        self.assertEqual(summary["exact_coordinate_fallbacks"], 1_696)
        self.assertEqual(summary["abstract_incidence_fallbacks"], 0)
        self.assertEqual(
            [task["bridge_point_count"] for task in self.committed["universe"]["target_tasks"]],
            [43, 42, 43, 43, 42, 43],
        )
        self.assertEqual(
            [
                task["deferred_circle_only_bridge_count"]
                for task in self.committed["universe"]["target_tasks"]
            ],
            [8, 8, 8, 6, 8, 8],
        )

    def test_only_existing_lines_are_constructible(self) -> None:
        summary = self.committed["summary"]
        self.assertEqual(summary["distinct_constructible_lines"], 643)
        self.assertEqual(summary["duplicate_constructible_lines"], 0)
        self.assertEqual(summary["constructible_existing_line_equalities"], 643)
        self.assertEqual(summary["constructible_new_lines"], 0)
        self.assertEqual(summary["distinct_constructible_new_lines"], 0)
        self.assertEqual(summary["shared_new_locator_lines"], 0)
        self.assertEqual(self.committed["constructible_new_line_candidates"], [])
        self.assertEqual(self.committed["shared_new_locator_candidates"], [])
        self.assertEqual(
            self.committed["conclusion"]["status"],
            "exhausted_no_shared_locator_line_with_prefix_line_witness",
        )

    @unittest.skip("完整可重复生成约需十余分钟；由构建命令和源哈希单独复核")
    def test_full_reproducibility(self) -> None:
        self.assertEqual(self.committed, build_report())


if __name__ == "__main__":
    unittest.main()
