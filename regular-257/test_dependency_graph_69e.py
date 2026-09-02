"""正 257 边形 69E 声明式依赖图测试。"""

from __future__ import annotations

import json
import unittest

import jsonschema

from build_69e_dependency_graph import (
    DOT_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)
from dependency_graph import render_paid_projection_dot


class Regular257DependencyGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_committed_report(self) -> None:
        schema = json.loads(
            (ROOT / "dependency-graph.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_graph_is_topologically_ordered(self) -> None:
        positions = {
            node["id"]: node["program_index"]
            for node in self.committed["nodes"]
        }
        for edge in self.committed["edges"]:
            self.assertLess(positions[edge["from"]], positions[edge["to"]])

    def test_every_paid_draw_feeds_the_final_draw(self) -> None:
        target = self.committed["target_analysis"]
        final_cone = target["final_paid_object_cone"]
        self.assertEqual(final_cone["root"], "target_transfer")
        self.assertEqual(final_cone["required_paid_nodes"], 69)
        self.assertEqual(final_cone["unrequired_paid_nodes"], [])
        self.assertEqual(target["removable_paid_draw_candidates"], [])
        for alternative in target["witness_alternatives"]:
            self.assertEqual(alternative["required_paid_nodes"], 69)
            self.assertEqual(alternative["unrequired_paid_nodes"], [])

    def test_paid_projection_and_dot_are_deterministic(self) -> None:
        projection = self.committed["paid_projection"]
        self.assertEqual(len(projection["nodes"]), 69)
        self.assertEqual(len(projection["edges"]), 209)
        final = projection["nodes"][-1]
        self.assertEqual(final["id"], "target_transfer")
        self.assertEqual(final["e_move"], 69)
        self.assertEqual(final["direct_paid_dependencies"], ["b", "BG0"])
        self.assertEqual(
            DOT_PATH.read_text(encoding="utf-8"),
            render_paid_projection_dot(self.fresh),
        )


if __name__ == "__main__":
    unittest.main()
