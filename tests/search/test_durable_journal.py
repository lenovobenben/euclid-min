from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

import jsonschema

from euclid_min.search.durable_journal import (
    DurableJournalError,
    append_event,
    load_journal,
    load_or_create_journal,
    task_definition,
)


class DurableJournalTests(unittest.TestCase):
    def task(self):
        return task_definition(
            task_id="test-candidate-search",
            input_sha256={"input": "0" * 64},
            configuration={"workers": 2},
            work_ids=("0", "1", "2"),
        )

    def test_append_pause_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.jsonl"
            snapshot = load_or_create_journal(path, task=self.task())
            snapshot = append_event(
                path,
                snapshot,
                event_type="result",
                payload={"work_id": "0", "hits": []},
            )
            snapshot = append_event(
                path,
                snapshot,
                event_type="status",
                payload={"status": "paused"},
            )
            resumed = load_or_create_journal(path, task=self.task())
            self.assertEqual(resumed, snapshot)
            self.assertEqual([event["type"] for event in resumed.events], [
                "result",
                "status",
            ])

    def test_truncated_final_record_is_discarded_before_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.jsonl"
            snapshot = load_or_create_journal(path, task=self.task())
            snapshot = append_event(
                path,
                snapshot,
                event_type="result",
                payload={"work_id": "0"},
            )
            valid_size = path.stat().st_size
            with path.open("ab") as stream:
                stream.write(b'{"sequence":1,"broken"')
            resumed = load_or_create_journal(path, task=self.task())
            self.assertEqual(resumed, snapshot)
            self.assertEqual(path.stat().st_size, valid_size)

    def test_middle_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.jsonl"
            snapshot = load_or_create_journal(path, task=self.task())
            append_event(
                path,
                snapshot,
                event_type="result",
                payload={"work_id": "0"},
            )
            data = path.read_bytes().replace(b'"work_id":"0"', b'"work_id":"9"')
            path.write_bytes(data)
            with self.assertRaises(DurableJournalError):
                load_journal(path)

    def test_task_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.jsonl"
            load_or_create_journal(path, task=self.task())
            changed = task_definition(
                task_id="test-candidate-search",
                input_sha256={"input": "1" * 64},
                configuration={"workers": 2},
                work_ids=("0", "1", "2"),
            )
            with self.assertRaises(DurableJournalError):
                load_or_create_journal(path, task=changed)

    def test_schemas_are_valid(self):
        repository_root = Path(__file__).resolve().parents[2]
        for name in (
            "durable-search-journal-event-v1.schema.json",
            "fixed-prefix-two-step-search-v2.schema.json",
        ):
            schema = json.loads(
                (repository_root / "schemas" / name).read_text(encoding="utf-8")
            )
            jsonschema.Draft202012Validator.check_schema(schema)


if __name__ == "__main__":
    unittest.main()
