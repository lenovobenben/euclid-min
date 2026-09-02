"""正 257 边形 69E 几何—代数统一 IR 测试。"""

from __future__ import annotations

import hashlib
import json
import unittest

import jsonschema

from build_69e_geometry_algebra_ir import (
    CERTIFICATE_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    ROOT,
    build_report,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257GeometryAlgebraIRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        cls.fresh = build_report()

    def test_schema_and_reproducibility(self) -> None:
        schema = json.loads(
            (ROOT / "geometry-algebra-ir.schema.json").read_text(encoding="utf-8")
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

    def test_contextual_cost_and_free_closure_partition(self) -> None:
        transitions = self.committed["transitions"]
        audit = self.committed["cost_audit"]
        self.assertEqual([item["e_move"] for item in transitions], list(range(1, 70)))
        self.assertEqual(sum(item["marginal_cost_e"] for item in transitions), 69)
        born = [
            point
            for transition in transitions
            for point in transition["free_points_born"]
        ]
        self.assertEqual(len(born), 2285)
        self.assertEqual(len(set(born)), 2285)
        self.assertEqual(audit["full_closure_points"], len(born) + 2)
        for transition in transitions:
            self.assertTrue(
                all(
                    birth < transition["e_move"]
                    for birth in transition["definition_point_birth_e_moves"]
                )
            )

    def test_algebra_graph_and_target_bridge(self) -> None:
        relation_ids = {
            relation["id"] for relation in self.committed["algebraic_relations"]
        }
        self.assertEqual(len(relation_ids), 17)
        self.assertIn("relation.g0", relation_ids)
        representations = {
            representation["id"]: representation
            for representation in self.committed["representations"]
        }
        self.assertEqual(len(representations), 42)
        self.assertEqual(representations["repr.K2"]["symbol"], "work.e-low-0")
        self.assertEqual(representations["repr.R2"]["symbol"], "work.e-high-1")
        self.assertEqual(
            representations["repr.auto.period.e16"]["symbol"],
            "period.e16",
        )
        self.assertEqual(
            representations["repr.auto.period.g64"]["symbol"],
            "period.g64",
        )
        self.assertTrue(
            all(
                len(relation["materialized_roots"]) == 2
                for relation in self.committed["algebraic_relations"]
            )
        )
        self.assertEqual(representations["repr.G0"]["symbol"], "period.g0")
        self.assertEqual(
            representations["repr.V2"]["symbol"], "coordinate.v2-x"
        )
        self.assertEqual(
            representations["repr.target-axis-g0"]["available_e_move"], 69
        )
        self.assertTrue(self.committed["consistency"]["target_bridge"]["verified"])

    def test_baseline_macro_partition(self) -> None:
        macros = self.committed["baseline_macro_partition"]
        self.assertEqual(len(macros), 11)
        self.assertEqual(
            sum(macro["observed_contextual_cost_e"] for macro in macros),
            69,
        )
        self.assertEqual(macros[0]["first_e_move"], 1)
        self.assertEqual(macros[-1]["last_e_move"], 69)
        by_id = {macro["id"]: macro for macro in macros}
        self.assertEqual(by_id["macro.b-pairs-joint"]["observed_contextual_cost_e"], 4)
        self.assertEqual(by_id["macro.low-tail"]["observed_contextual_cost_e"], 9)
        self.assertEqual(by_id["macro.high-tail"]["observed_contextual_cost_e"], 9)


if __name__ == "__main__":
    unittest.main()
