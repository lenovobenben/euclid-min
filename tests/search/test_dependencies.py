from __future__ import annotations

import json
import unittest
from pathlib import Path

from euclid_min.search.dependencies import (
    audit_first_target_ancestry,
    audit_paid_ancestry,
    build_dependency_map,
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


if __name__ == "__main__":
    unittest.main()
