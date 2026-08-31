from __future__ import annotations

import json
import unittest
from pathlib import Path

from euclid_min.search.dependencies import (
    audit_first_target_ancestry,
    audit_paid_ancestry,
    build_dependency_map,
    build_reverse_dependency_dag,
    prune_program_to_ancestors,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMPROVED_CERTIFICATE = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)


class DependencyAncestryTests(unittest.TestCase):
    def test_non_ancestor_paid_object_can_be_structurally_pruned(self):
        program = [
            {
                "id": "C1",
                "op": "circle",
                "center": "A",
                "through": "O",
            },
            {
                "id": "P1",
                "op": "intersect",
                "objects": ["C1", "unit_circle"],
                "index": 0,
            },
            {"id": "L1", "op": "line", "through": ["O", "P1"]},
            {"id": "junk", "op": "line", "through": ["O", "A"]},
        ]

        audit = audit_paid_ancestry(program, ("L1",))
        pruned = prune_program_to_ancestors(program, ("L1",))

        self.assertEqual(audit.paid_objects, frozenset({"C1", "L1", "junk"}))
        self.assertEqual(audit.non_ancestor_paid_objects, frozenset({"junk"}))
        self.assertFalse(audit.all_paid_objects_are_ancestors)
        self.assertEqual(
            [entry["id"] for entry in pruned],
            ["C1", "P1", "L1"],
        )

    def test_dependency_map_rejects_forward_references(self):
        with self.assertRaises(ValueError):
            build_dependency_map(
                [{"id": "L1", "op": "line", "through": ["O", "future"]}]
            )

    def test_verified_19e_program_has_no_paid_non_ancestor(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        audit = audit_first_target_ancestry(certificate["construction"]["program"])

        self.assertEqual(audit.roots, ("target_line",))
        self.assertEqual(len(audit.paid_objects), 19)
        self.assertTrue(audit.all_paid_objects_are_ancestors)

    def test_reverse_dag_uses_automatic_closure_availability(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        dag = build_reverse_dependency_dag(
            certificate["construction"]["program"],
            ("target_line",),
        )

        self.assertEqual(dag.total_paid_cost, 19)
        self.assertEqual(dag.node("target_line").availability_score, 19)
        # 该交点在程序的 13 E 位置才命名，但它的两个父对象在 8 E 已存在；
        # 自动闭包语义下它从 8 E 起就可用。
        self.assertEqual(dag.node("positive_half").availability_score, 8)

    def test_reverse_dag_cuts_known_19e_suffix(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        dag = build_reverse_dependency_dag(
            certificate["construction"]["program"],
            ("target_line",),
        )

        cut17 = dag.cut(17)
        self.assertEqual(
            cut17.boundary,
            ("O", "Q", "c_Q_O", "H4_8"),
        )
        self.assertEqual(cut17.boundary_points, ("O", "Q", "H4_8"))
        self.assertEqual(cut17.boundary_drawables, ("c_Q_O",))
        self.assertEqual(
            cut17.suffix_paid_nodes,
            ("target_helper_circle", "target_line"),
        )
        self.assertEqual(cut17.suffix_paid_cost, 2)

        cut18 = dag.cut(18)
        self.assertEqual(cut18.boundary, ("Q", "target_helper_point"))
        self.assertEqual(cut18.suffix_paid_nodes, ("target_line",))

        for score in range(20):
            cut = dag.cut(score)
            self.assertEqual(cut.suffix_paid_cost, 19 - score)
            self.assertTrue(
                all(
                    dag.node(node_id).availability_score <= score
                    for node_id in cut.boundary
                )
            )
            self.assertTrue(
                all(
                    dag.node(node_id).availability_score > score
                    for node_id in cut.suffix_nodes
                )
            )

    def test_reverse_dag_prunes_irrelevant_paid_nodes_before_scoring(self):
        program = [
            {"id": "junk", "op": "line", "through": ["O", "A"]},
            {
                "id": "C1",
                "op": "circle",
                "center": "A",
                "through": "O",
            },
            {
                "id": "P1",
                "op": "intersect",
                "objects": ["C1", "unit_circle"],
                "index": 0,
            },
            {"id": "L1", "op": "line", "through": ["O", "P1"]},
        ]

        dag = build_reverse_dependency_dag(program, ("L1",))

        self.assertEqual(dag.total_paid_cost, 2)
        self.assertEqual(dag.node("C1").paid_index, 1)
        self.assertEqual(dag.node("L1").paid_index, 2)
        with self.assertRaises(KeyError):
            dag.node("junk")

    def test_reverse_dag_rejects_negative_cut(self):
        dag = build_reverse_dependency_dag([], ("unit_circle",))

        with self.assertRaises(ValueError):
            dag.cut(-1)

        with self.assertRaises(ValueError):
            build_reverse_dependency_dag([], ())


if __name__ == "__main__":
    unittest.main()
