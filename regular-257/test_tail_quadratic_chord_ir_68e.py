"""正 257 边形尾部二次根载线 IR 测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_68e_tail_quadratic_chord_ir import (
    CERTIFICATE_PATH,
    FULL_CLOSURE_PATH,
    GA_IR_PATH,
    LIVE_SLICE_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257TailQuadraticChordIRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (ROOT / "tail-quadratic-chord-ir.schema.json").read_text(
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
            source["geometry_algebra_ir_sha256"], sha256_file(GA_IR_PATH)
        )
        self.assertEqual(
            source["full_intersection_closure_sha256"],
            sha256_file(FULL_CLOSURE_PATH),
        )
        self.assertEqual(
            source["synthesis_live_slice_sha256"], sha256_file(LIVE_SLICE_PATH)
        )

    def test_six_formula_lines_are_exact(self) -> None:
        tasks = self.committed["tasks"]
        self.assertEqual(len(tasks), 6)
        self.assertEqual(
            [task["baseline_carrier"] for task in tasks],
            ["H2Y1", "AJ2", "L2I2", "M2O2", "AQ2", "S2P2"],
        )
        for task in tasks:
            self.assertTrue(
                all(task["verification"].values()),
                task["id"],
            )
            self.assertNotEqual(
                task["demanded_root"], task["free_sibling_byproduct"]
            )

    def test_46e_prefix_incidence(self) -> None:
        tasks = {task["baseline_carrier"]: task for task in self.committed["tasks"]}
        self.assertEqual(tasks["AJ2"]["available_incident_points_at_46e"], ["A"])
        self.assertEqual(tasks["AQ2"]["available_incident_points_at_46e"], ["A"])
        for carrier in ("H2Y1", "L2I2", "M2O2", "S2P2"):
            self.assertFalse(tasks[carrier]["available_incident_points_at_46e"])
        summary = self.committed["summary"]
        self.assertEqual(summary["tasks_with_any_available_incident_point_at_46e"], 2)
        self.assertEqual(summary["tasks_with_two_available_incident_points_at_46e"], 0)
        self.assertEqual(summary["distinct_available_incident_points_at_46e"], ["A"])


if __name__ == "__main__":
    unittest.main()
