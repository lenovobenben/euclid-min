from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from euclid_min.verifier import verify_files


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMPROVED_DIRECTORY = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
)
BASELINE_CERTIFICATE = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-converted"
    / "construction.json"
)
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
GRAPH_SCHEMA_PATH = REPOSITORY_ROOT / "schemas" / "dependency-graph-v1.schema.json"


class DeTempleImprovedTests(unittest.TestCase):
    def test_improved_construction_is_a_verified_19_e_upper_bound(self):
        report = verify_files(IMPROVED_DIRECTORY / "construction.json", PROFILE_PATH)

        self.assertTrue(report.valid)
        self.assertEqual(report.data["score"], {"metric": "e_move", "e_move": 19})
        self.assertEqual(
            report.data["draw_operations"],
            {"lines": 8, "circles": 11, "total": 19},
        )
        self.assertEqual(report.data["targets"], ["B_plus"])
        self.assertEqual(report.data["first_target_e_move"], 19)
        self.assertEqual(report.data["duplicate_draws"], 0)

        baseline = json.loads(BASELINE_CERTIFICATE.read_text(encoding="utf-8"))
        baseline_score = baseline["assertions"]["score"]["e_move"]
        self.assertEqual(baseline_score - report.data["score"]["e_move"], 13)

    def test_dependency_graph_matches_certificate_program(self):
        certificate = json.loads(
            (IMPROVED_DIRECTORY / "construction.json").read_text(encoding="utf-8")
        )
        graph = json.loads(
            (IMPROVED_DIRECTORY / "dependency-graph.json").read_text(
                encoding="utf-8"
            )
        )
        schema = json.loads(GRAPH_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(graph)

        self.assertEqual(
            graph["construction_sha256"],
            certificate["integrity"]["construction_sha256"],
        )
        self.assertEqual(graph["profile"], certificate["profile"])
        self.assertEqual(graph["total_e_move"], 19)

        program = certificate["construction"]["program"]
        program_nodes = graph["nodes"][3:]
        self.assertEqual(
            [node["id"] for node in program_nodes],
            [entry["id"] for entry in program],
        )

        available = {"O", "A", "unit_circle"}
        cost = 0
        for entry, node in zip(program, program_nodes):
            expected_dependencies = (
                entry["through"]
                if entry["op"] == "line"
                else [entry["center"], entry["through"]]
                if entry["op"] == "circle"
                else entry["objects"]
            )
            self.assertEqual(node["depends_on"], expected_dependencies)
            self.assertTrue(set(expected_dependencies) <= available)
            cost += int(entry["op"] in {"line", "circle"})
            self.assertEqual(node["e_move_after"], cost)
            available.add(entry["id"])
        self.assertEqual(cost, 19)

        nodes_by_id = {node["id"]: node for node in graph["nodes"]}
        pending = ["target_line"]
        live: set[str] = set()
        while pending:
            node_id = pending.pop()
            if node_id in live:
                continue
            live.add(node_id)
            pending.extend(nodes_by_id[node_id]["depends_on"])
        paid_nodes = {node["id"] for node in graph["nodes"] if node["cost"] == 1}
        self.assertEqual(paid_nodes - live, set())


if __name__ == "__main__":
    unittest.main()
