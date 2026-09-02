from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import jsonschema

from euclid_min.search.sharded_checkpoint import load_checkpoint
from experiments.search_e17_one_step_target_extension import (
    DEFAULT_CHECKPOINT,
    DEFAULT_SUMMARY,
    REPOSITORY_ROOT,
    SEARCH_SCRIPT_PATH,
)


class E17OneStepTargetExtensionArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = json.loads(DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        cls.checkpoint = load_checkpoint(DEFAULT_CHECKPOINT)

    def test_artifacts_validate_against_schemas(self):
        for filename, instance in (
            ("fixed-prefix-one-step-search-v1.schema.json", self.summary),
            ("sharded-search-checkpoint-v1.schema.json", self.checkpoint),
        ):
            schema = json.loads(
                (REPOSITORY_ROOT / "schemas" / filename).read_text(encoding="utf-8")
            )
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(schema).validate(instance)

    def test_checkpoint_is_complete_and_covers_every_parameterization(self):
        progress = self.checkpoint["progress"]
        task = self.checkpoint["task"]
        self.assertEqual(progress["status"], "completed")
        self.assertEqual(len(progress["completed_shards"]), len(task["shard_ids"]))
        self.assertEqual(len(task["shard_ids"]), 126)
        self.assertEqual(
            sum(item["result"]["tested"] for item in progress["completed_shards"]),
            32193,
        )
        script_key = str(SEARCH_SCRIPT_PATH.relative_to(REPOSITORY_ROOT)).replace(
            "\\", "/"
        )
        self.assertEqual(
            task["input_sha256"][script_key],
            hashlib.sha256(SEARCH_SCRIPT_PATH.read_bytes()).hexdigest(),
        )

    def test_exact_result_closes_only_the_fixed_prefix_one_step_route(self):
        coverage = self.summary["coverage"]
        self.assertEqual(self.summary["scope"]["prefix_points"], 147)
        self.assertEqual(coverage["line_parameterizations"], 10731)
        self.assertEqual(coverage["circle_parameterizations"], 21462)
        self.assertEqual(coverage["tested_parameterizations"], 32193)
        self.assertEqual(coverage["target_incident_parameterizations"], 15)
        self.assertEqual(coverage["existing_object_parameterizations"], 15)
        self.assertEqual(self.summary["result"]["unique_new_target_objects"], 0)
        reference = self.summary["reference_replay"]
        self.assertEqual(reference["unique_new_candidates"], 30021)
        self.assertEqual(reference["unique_new_target_objects"], 0)
        self.assertTrue(reference["agrees_with_sharded_scan"])

    def test_summary_and_checkpoint_signatures_match(self):
        self.assertEqual(
            self.summary["checkpoint"]["task_signature"],
            self.checkpoint["task"]["signature"],
        )


if __name__ == "__main__":
    unittest.main()
