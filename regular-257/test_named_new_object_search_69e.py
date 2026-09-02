"""正 257 边形 69E 具名点单新对象替换搜索测试。"""

from __future__ import annotations

import hashlib
import json
import unittest
from math import comb

import jsonschema

from named_new_object_search import search_named_replacements
from run_69e_named_new_object_search import (
    CERTIFICATE_PATH,
    FULL_CLOSURE_PATH,
    OUTPUT_PATH,
    ROOT,
    SEMANTIC_PATH,
)


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Regular257NamedNewObjectSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    def test_schema_and_source_hashes(self) -> None:
        schema = json.loads(
            (ROOT / "named-new-object-search.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.report)
        source = self.report["source"]
        self.assertEqual(source["certificate_sha256"], sha256_file(CERTIFICATE_PATH))
        self.assertEqual(
            source["semantic_dependency_report_sha256"],
            sha256_file(SEMANTIC_PATH),
        )
        self.assertEqual(
            source["full_intersection_closure_report_sha256"],
            sha256_file(FULL_CLOSURE_PATH),
        )

    def test_candidate_enumeration_counts(self) -> None:
        enumeration = self.report["enumeration"]
        self.assertEqual(enumeration["point_pairs"], comb(83, 2))
        self.assertEqual(enumeration["point_triples"], comb(83, 3))
        self.assertEqual(enumeration["circle_radius_pairs"], 83 * comb(82, 2))
        candidates = self.report["candidates"]
        lines = [item for item in candidates if item["kind"] == "line"]
        circles = [item for item in candidates if item["kind"] == "circle"]
        self.assertEqual(len(lines), 4)
        self.assertEqual(len(circles), 143)
        for line in lines:
            point_count = len(line["incident_named_points"])
            self.assertEqual(line["definition_count"], comb(point_count, 2))
        for circle in circles:
            self.assertEqual(
                circle["definition_count"],
                len(circle["incident_named_points"]),
            )

    def test_exhaustive_search_accounting_and_result(self) -> None:
        search = self.report["search"]
        self.assertEqual(search["removed_pairs_tested"], comb(69, 2))
        self.assertEqual(
            search["closure_trials"],
            search["removed_pairs_tested"] * search["candidate_count"],
        )
        self.assertEqual(search["solutions"], [])
        self.assertEqual(search["solutions_found"], 0)
        self.assertEqual(search["status"], "exhausted_no_solution")

    def test_search_state_can_resume_at_last_pair(self) -> None:
        semantic_report = json.loads(SEMANTIC_PATH.read_text(encoding="utf-8"))
        candidate = self.report["candidates"][0]
        state = {
            "target_score": 68,
            "removed_old_draws": 2,
            "added_new_draws": 1,
            "removed_pairs_tested": 2345,
            "next_removed_pair_index": 2345,
            "candidate_count": 1,
            "closure_trials": 2345,
            "constructible_candidate_trials": 0,
            "solutions": [],
            "solutions_found": 0,
            "status": "running",
        }
        completed = search_named_replacements(
            semantic_report,
            [candidate],
            state=state,
        )
        self.assertEqual(completed["next_removed_pair_index"], 2346)
        self.assertEqual(completed["closure_trials"], 2346)
        self.assertIn(completed["status"], {"solution_found", "exhausted_no_solution"})


if __name__ == "__main__":
    unittest.main()
