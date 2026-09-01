"""两个 9E 尾部 gadget 的边界、成本与精确重放测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_69e_tail_gadgets import (
    CERTIFICATE_PATH,
    GA_IR_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257TailGadgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (ROOT / "geometry-gadget.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.committed)
        self.assertEqual(self.committed, self.fresh)

    def test_source_hashes(self) -> None:
        source = self.committed["source"]
        self.assertEqual(source["certificate_sha256"], sha256_file(CERTIFICATE_PATH))
        self.assertEqual(
            source["geometry_algebra_ir_sha256"],
            sha256_file(GA_IR_PATH),
        )

    def test_tail_interfaces_and_contextual_costs(self) -> None:
        gadgets = {gadget["id"]: gadget for gadget in self.committed["gadgets"]}
        low = gadgets["gadget.low-tail-9e"]
        high = gadgets["gadget.high-tail-9e"]
        self.assertEqual(low["context"]["before_e_move"], 46)
        self.assertEqual(high["context"]["before_e_move"], 55)
        for gadget in (low, high):
            self.assertEqual(gadget["cost"]["e_move"], 9)
            self.assertEqual(gadget["cost"]["lines"], 9)
            self.assertEqual(gadget["cost"]["circles"], 0)
            self.assertEqual(gadget["cost"]["duplicate_drawables"], 0)
            self.assertEqual(len(gadget["program"]), 18)
            self.assertEqual(len(gadget["effects"]["new_paid_drawables"]), 9)
            self.assertEqual(len(gadget["effects"]["explicit_points_bound"]), 9)
        self.assertEqual(
            low["algebraic_interface"]["output_symbols"],
            [
                "period.e0",
                "period.e16",
                "work.e-low-0",
                "work.e-low-1",
                "period.f0",
                "period.f32",
            ],
        )
        self.assertEqual(
            high["algebraic_interface"]["output_symbols"],
            [
                "period.e8",
                "period.e24",
                "work.e-high-0",
                "work.e-high-1",
                "period.f24",
                "period.f56",
            ],
        )

    def test_shared_trace_boundary(self) -> None:
        comparison = self.committed["comparison"]
        self.assertEqual(comparison["baseline_combined_cost_e"], 18)
        self.assertEqual(
            comparison["shared_required_points"],
            ["A", "B", "D", "E", "G"],
        )
        self.assertEqual(
            comparison["shared_required_drawables"],
            ["a", "b", "c"],
        )
        self.assertEqual(comparison["minimality_claim"], "none")


if __name__ == "__main__":
    unittest.main()
