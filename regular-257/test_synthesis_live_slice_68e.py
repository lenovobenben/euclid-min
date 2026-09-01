"""正 257 边形 68E 合成活跃切片测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_68e_synthesis_live_slice import (
    CERTIFICATE_PATH,
    GADGET_LIBRARY_PATH,
    GA_IR_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257SynthesisLiveSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (ROOT / "synthesis-live-slice.schema.json").read_text(encoding="utf-8")
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
            source["geometry_gadget_library_sha256"],
            sha256_file(GADGET_LIBRARY_PATH),
        )

    def test_algebraic_liveness(self) -> None:
        algebra = self.committed["algebraic_slice"]
        summary = algebra["summary"]
        self.assertEqual(summary["quadratic_roots_total"], 34)
        self.assertEqual(summary["demanded_quadratic_roots"], 23)
        self.assertEqual(summary["free_sibling_byproduct_roots"], 11)
        self.assertEqual(summary["inactive_quadratic_roots"], 0)
        self.assertEqual(summary["active_relations"], 17)
        self.assertEqual(summary["inactive_relations"], 0)
        self.assertIn("period.g0", algebra["active_quadratic_roots"])
        self.assertIn("period.g64", algebra["free_sibling_byproduct_roots"])
        self.assertIn("work.ca-conjugate", algebra["free_sibling_byproduct_roots"])

    def test_reduced_joint_tail_contract(self) -> None:
        contract = self.committed["synthesis_contract"]
        self.assertEqual(contract["input_state_after_e_move"], 46)
        self.assertEqual(
            contract["required_output_symbols"], ["period.f0", "period.f56"]
        )
        self.assertEqual(
            contract["required_output_representations"], ["repr.F0", "repr.F56"]
        )
        self.assertEqual(contract["baseline_contextual_cost_e"], 18)
        self.assertEqual(contract["maximum_candidate_contextual_cost_e"], 17)
        self.assertEqual(contract["downstream_fixed_suffix_cost_e"], 5)
        self.assertEqual(contract["resulting_total_upper_bound_e"], 68)
        self.assertEqual(
            set(contract["internal_demanded_symbols_not_in_output_interface"]),
            {"period.e0", "work.e-low-0", "period.e24", "work.e-high-1"},
        )
        self.assertEqual(
            len(contract["free_sibling_byproducts_not_in_output_interface"]), 6
        )

    def test_no_baseline_tail_dead_drawable(self) -> None:
        regions = {
            region["id"]: region
            for region in self.committed["geometric_slice"]["tail_regions"]
        }
        self.assertEqual(len(regions["low-tail-47-55"]["live_paid_drawables"]), 9)
        self.assertEqual(len(regions["high-tail-56-64"]["live_paid_drawables"]), 9)
        self.assertEqual(len(regions["joint-tail-47-64"]["live_paid_drawables"]), 18)
        self.assertTrue(
            all(not region["directly_dead_paid_drawables"] for region in regions.values())
        )


if __name__ == "__main__":
    unittest.main()
