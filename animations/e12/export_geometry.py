"""Export the exactly verified web snapshot to Manim without solving geometry.

The web exporter replays the certificate twice in Sage AA before serializing
12-place decimal strings. This adapter checks its recorded SHA-256 hashes and
the complete program, then changes only the screen coordinate convention.
Run with ordinary Python; regenerate the upstream snapshot with Sage first
whenever the certificate changes.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CERTIFICATE = ROOT / "qq-ggb/construction-12e-011.json"
WEB_DATA = ROOT / "qq-ggb/web/geometry.json"
WEB_REPORT = ROOT / "qq-ggb/web/export-report.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def xy(point: list[str]) -> list[str]:
    # SVG has a downward y axis; mathematical and Manim coordinates point up.
    return [point[0], str(-Decimal(point[1]))]


def build_export() -> dict:
    raw = CERTIFICATE.read_bytes()
    certificate = json.loads(raw)
    web_raw = WEB_DATA.read_bytes()
    web = json.loads(web_raw)
    report = json.loads(WEB_REPORT.read_text(encoding="utf-8"))
    digest = hashlib.sha256(raw).hexdigest()
    require(report["passed"] is True, "Upstream exact export did not pass")
    require(hashlib.sha256(web_raw).hexdigest() == report["geometry_sha256"],
            "Web geometry changed: regenerate it with Sage")
    require(digest == web["source"]["certificate_sha256"] == report["certificate_sha256"],
            "Certificate changed: regenerate web geometry with Sage")
    require(certificate == web["certificate"], "Embedded certificate differs")
    require(certificate["integrity"]["construction_sha256"] == web["source"]["construction_sha256"],
            "Construction digest differs")
    require(certificate["profile"]["sha256"] == web["source"]["profile_sha256"],
            "Profile digest differs")
    require(web["verified"] == {
        "e": 12, "lines": 3, "paidCircles": 9, "firstTarget": 12,
        "targets": ["ggb_Q", "ggb_R"], "independentReplay": True,
    }, "Unexpected verified construction")
    require(report["exact_independent_point_comparisons"] == 18,
            "Missing independent point comparisons")

    program = certificate["construction"]["program"]
    draws = [entry for entry in program if entry["op"] != "intersect"]
    require(len(draws) == len(web["steps"]) == 12, "Expected twelve charged steps")
    points = {key: {**value, "xy": xy(value["xy"])} for key, value in web["points"].items()}
    require(len(points) == 18, "Expected eighteen named points")
    births = {"O": 0, "A": 0, "unit_circle": 0}
    e_move = 0
    for entry in program:
        if entry["op"] == "intersect":
            births[entry["id"]] = max(births[key] for key in entry["objects"])
        else:
            e_move += 1
            births[entry["id"]] = e_move
    for key, point in points.items():
        require(point["birth"] == births[key], f"Incorrect point birth: {key}")

    steps = []
    for index, (entry, original) in enumerate(zip(draws, web["steps"], strict=True), 1):
        refs = entry["through"] if entry["op"] == "line" else [entry["center"], entry["through"]]
        require((original["e"], original["id"], original["op"], original["refs"]) ==
                (index, entry["id"], entry["op"], refs), "Step differs from certificate")
        require(all(births[key] < index for key in refs), "Reference not available before drawing")
        x0, y0, x1, y1 = original["frame"]
        step = {"e": index, "id": entry["id"], "op": entry["op"], "refs": refs,
                "frame": [x0, str(-Decimal(y1)), x1, str(-Decimal(y0))]}
        if entry["op"] == "line":
            step["ends"] = [xy(point) for point in original["ends"]]
        else:
            step.update(center=xy(original["center"]), radius=original["radius"])
        steps.append(step)
    return {
        "schema": "euclid-min-manim-e12/v1",
        "source": {**web["source"], "certificate": "qq-ggb/construction-12e-011.json",
                   "web_geometry_sha256": report["geometry_sha256"]},
        "verified_result": {"e_move": 12, "line_draws": 3, "circle_draws": 9,
                            "first_target_e_move": 12, "targets": ["B_plus", "B_minus"]},
        "display": web["display"], "points": points, "steps": steps,
    }


if __name__ == "__main__":
    output = HERE / "geometry.json"
    output.write_text(json.dumps(build_export(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
