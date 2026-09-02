from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from euclid_min.search.sharded_checkpoint import (
    ShardedCheckpointError,
    load_checkpoint,
    load_or_create_checkpoint,
    record_completed_shard,
    remaining_shard_ids,
    set_checkpoint_status,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
INPUT_PATH = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)


class ShardedCheckpointTests(unittest.TestCase):
    def definition(self):
        return {
            "task_id": "test-sharded-search",
            "profile_path": PROFILE_PATH,
            "input_sha256": {
                "construction.json": hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest()
            },
            "configuration": {"prefix_e_move": 17, "shard_size": 64},
            "shard_ids": ["0000", "0001", "0002"],
        }

    def test_create_record_pause_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            payload = load_or_create_checkpoint(path, **self.definition())
            self.assertEqual(remaining_shard_ids(payload), ("0000", "0001", "0002"))

            payload = record_completed_shard(
                path,
                payload,
                shard_id="0000",
                result={"tested": 64, "hits": []},
            )
            payload = set_checkpoint_status(path, payload, "paused")
            resumed = load_or_create_checkpoint(path, **self.definition())
            self.assertEqual(resumed["progress"]["status"], "paused")
            self.assertEqual(remaining_shard_ids(resumed), ("0001", "0002"))

            resumed = set_checkpoint_status(path, resumed, "running")
            resumed = record_completed_shard(
                path,
                resumed,
                shard_id="0001",
                result={"tested": 64, "hits": []},
            )
            resumed = record_completed_shard(
                path,
                resumed,
                shard_id="0002",
                result={"tested": 5, "hits": []},
            )
            resumed = set_checkpoint_status(path, resumed, "completed")
            final = load_checkpoint(path)
            self.assertEqual(final["progress"]["status"], "completed")
            self.assertEqual(remaining_shard_ids(final), ())
            self.assertFalse(list(Path(directory).glob("*.tmp")))

    def test_same_completed_result_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            payload = load_or_create_checkpoint(path, **self.definition())
            payload = record_completed_shard(
                path,
                payload,
                shard_id="0000",
                result={"tested": 1},
            )
            same = record_completed_shard(
                path,
                payload,
                shard_id="0000",
                result={"tested": 1},
            )
            self.assertEqual(same, payload)
            with self.assertRaises(ShardedCheckpointError):
                record_completed_shard(
                    path,
                    payload,
                    shard_id="0000",
                    result={"tested": 2},
                )

    def test_definition_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            load_or_create_checkpoint(path, **self.definition())
            changed = self.definition()
            changed["configuration"] = {"prefix_e_move": 16, "shard_size": 64}
            with self.assertRaises(ShardedCheckpointError):
                load_or_create_checkpoint(path, **changed)

    def test_signature_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            load_or_create_checkpoint(path, **self.definition())
            data = json.loads(path.read_text(encoding="utf-8"))
            data["task"]["configuration"]["prefix_e_move"] = 16
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ShardedCheckpointError):
                load_checkpoint(path)


if __name__ == "__main__":
    unittest.main()
