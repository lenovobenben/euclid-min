from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from euclid_min.cli import main


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
CERTIFICATE_PATH = (
    REPOSITORY_ROOT / "tests" / "fixtures" / "certificates" / "not-target.json"
)


class CliTests(unittest.TestCase):
    def test_human_failure_output_and_exit_code(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "verify",
                    "--profile",
                    str(PROFILE_PATH),
                    str(CERTIFICATE_PATH),
                ]
            )
        self.assertEqual(exit_code, 1)
        self.assertIn("构造有效：否", output.getvalue())
        self.assertIn("target_not_reached", output.getvalue())

    def test_json_stdout_and_report_file(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.json"
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "verify",
                        "--json",
                        "--report",
                        str(report_path),
                        "--profile",
                        str(PROFILE_PATH),
                        str(CERTIFICATE_PATH),
                    ]
                )
            stdout_report = json.loads(output.getvalue())
            file_report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_report, file_report)
        self.assertFalse(stdout_report["valid"])

    def test_search_json_reports_bounded_exhaustion(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "search",
                    "--profile",
                    str(PROFILE_PATH),
                    "--max-score",
                    "0",
                    "--json",
                ]
            )
        self.assertEqual(exit_code, 1)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary["status"], "exhausted")
        self.assertEqual(summary["max_score"], 0)
        self.assertEqual(summary["stats"]["expanded_states"], 0)


if __name__ == "__main__":
    unittest.main()
