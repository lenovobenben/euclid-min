"""46E 具名前缀跨尾部一笔联合产出搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_46e_tail_cross_pair_search import (
    CERTIFICATE_PATH,
    GADGET_PATH,
    GA_IR_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257TailCrossPairSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (ROOT / "tail-cross-pair-search.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_source_hashes(self) -> None:
        source = self.committed["source"]
        self.assertEqual(source["certificate_sha256"], sha256_file(CERTIFICATE_PATH))
        self.assertEqual(source["geometry_algebra_ir_sha256"], sha256_file(GA_IR_PATH))
        self.assertEqual(
            source["tail_gadget_library_sha256"],
            sha256_file(GADGET_PATH),
        )

    def test_complete_cross_product_and_geometry_deduplication(self) -> None:
        summary = self.committed["summary"]
        self.assertEqual(summary["prefix_named_points"], 59)
        self.assertEqual(summary["prefix_drawables"], 47)
        self.assertEqual(summary["cross_root_pairs"], 36)
        self.assertEqual(len(self.committed["results"]), 36)
        self.assertEqual(
            {
                (result["low_symbol"], result["high_symbol"])
                for result in self.committed["results"]
            },
            {
                (low, high)
                for low in self.committed["root_sets"]["low_tail"]
                for high in self.committed["root_sets"]["high_tail"]
            },
        )
        self.assertEqual(summary["line_definitions_found"], 0)
        self.assertEqual(summary["circle_definitions_found"], 1080)
        self.assertEqual(summary["existing_redraw_definitions"], 1080)
        self.assertEqual(summary["new_direct_definitions_found"], 0)
        self.assertEqual(summary["distinct_new_line_geometries_found"], 0)
        self.assertEqual(summary["distinct_new_circle_geometries_found"], 0)
        self.assertEqual(summary["root_pairs_with_direct_realization"], 0)
        self.assertEqual(self.committed["root_pair_hits"], [])
        self.assertEqual(
            self.committed["conclusion"]["status"],
            "exhausted_no_candidate",
        )

    def test_all_circle_syntax_hits_are_existing_encoding_circle(self) -> None:
        for result in self.committed["results"]:
            self.assertEqual(result["new_direct_definition_count"], 0)
            self.assertEqual(len(result["circles"]), 1)
            circle = result["circles"][0]
            self.assertEqual(circle["center"], "A")
            self.assertEqual(circle["new_definition_count"], 0)
            self.assertEqual(circle["existing_drawable_references"], ["c"])


if __name__ == "__main__":
    unittest.main()
