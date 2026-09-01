"""M257-8 最大前沿全部点单个最终对象汇总报告测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_68e_all_point_direct_search_summary import (
    CIRCLE_PATH,
    LINE_ADJACENT_PATH,
    LINE_CHORD_PATH,
    OUTPUT_PATH,
    POINT_AUDIT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257AllPointDirectSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "all-point-direct-search.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.report)
        source = self.report["source"]
        expected = {
            "residual_point_ball_audit_sha256": POINT_AUDIT_PATH,
            "line_chord_report_sha256": LINE_CHORD_PATH,
            "line_adjacent_report_sha256": LINE_ADJACENT_PATH,
            "circle_report_sha256": CIRCLE_PATH,
        }
        for key, path in expected.items():
            self.assertEqual(source[key], sha256_file(path))

    def test_report_is_reproducible(self) -> None:
        self.assertEqual(self.report, build_report())

    def test_complete_definition_universe(self) -> None:
        universe = self.report["universe"]
        point_count = universe["available_points"]
        self.assertEqual(
            universe["line_definitions"], point_count * (point_count - 1) // 2
        )
        self.assertEqual(
            universe["circle_definitions"], point_count * (point_count - 1)
        )
        self.assertEqual(
            universe["drawable_definitions"],
            universe["line_definitions"] + universe["circle_definitions"],
        )
        self.assertEqual(self.report["search"]["unresolved_definitions"], 0)
        self.assertEqual(self.report["search"]["solutions_found"], 0)


if __name__ == "__main__":
    unittest.main()
