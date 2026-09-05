"""Verify the 17 E certificate and refresh its checked-in report."""

from __future__ import annotations

import json
from pathlib import Path

from euclid_min.verifier import verify_files


BASELINE_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

report = verify_files(
    BASELINE_DIRECTORY / "construction.json",
    REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml",
)
BASELINE_DIRECTORY.joinpath("verification.json").write_text(
    json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
assert report.valid
