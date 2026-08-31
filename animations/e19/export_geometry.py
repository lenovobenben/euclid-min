"""从已验证 19 E 证书导出 Manim 所需的数值几何快照。"""

from __future__ import annotations

import json
from pathlib import Path

from euclid_min.geometry import Circle, Line, Point
from euclid_min.replay import ProgramReplayer
from euclid_min.target import TargetName, adjacent_targets


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CERTIFICATE_PATH = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)
VERIFICATION_PATH = CERTIFICATE_PATH.with_name("verification.json")
OUTPUT_PATH = Path(__file__).with_name("geometry.json")


def _point_data(point: Point) -> list[float]:
    return [float(point.x), float(point.y)]


def _drawable_data(drawable: Line | Circle) -> dict:
    if isinstance(drawable, Line):
        return {
            "a": float(drawable.a),
            "b": float(drawable.b),
            "c": float(drawable.c),
        }
    return {
        "center": _point_data(drawable.center),
        "radius": float(drawable.radius_squared.sqrt()),
    }


def build_export() -> dict:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    verification = json.loads(VERIFICATION_PATH.read_text(encoding="utf-8"))
    program = certificate["construction"]["program"]
    replay = ProgramReplayer().replay(program)

    events: list[dict] = []
    e_move = 0
    for program_index, entry in enumerate(program):
        operation = entry["op"]
        named_object = replay.names[entry["id"]]
        if operation in {"line", "circle"}:
            e_move += 1
            event = {
                "kind": "draw",
                "program_index": program_index,
                "e_move": e_move,
                "id": entry["id"],
                "op": operation,
                "geometry": _drawable_data(named_object),
            }
            if operation == "line":
                event["through"] = entry["through"]
            else:
                event["center"] = entry["center"]
                event["through"] = entry["through"]
        else:
            event = {
                "kind": "intersection",
                "program_index": program_index,
                "after_e_move": e_move,
                "id": entry["id"],
                "objects": entry["objects"],
                "point": _point_data(named_object),
            }
        events.append(event)

    points = {
        name: _point_data(value)
        for name, value in sorted(replay.names.items())
        if isinstance(value, Point)
    }
    target = adjacent_targets()[TargetName.B_PLUS]
    if replay.e_move != 19 or replay.first_target_e_move != 19:
        raise RuntimeError("权威证书不再是首次于 19 E 命中的构造")

    return {
        "schema": "euclid-min-manim-e19/v1",
        "source": {
            "certificate": str(CERTIFICATE_PATH.relative_to(REPOSITORY_ROOT)),
            "certificate_sha256": verification["certificate_sha256"],
            "construction_sha256": certificate["integrity"][
                "construction_sha256"
            ],
            "profile_id": certificate["profile"]["id"],
            "profile_sha256": certificate["profile"]["sha256"],
            "sage_version": verification["verifier"]["sage_version"],
        },
        "verified_result": {
            "e_move": replay.e_move,
            "line_draws": replay.line_draws,
            "circle_draws": replay.circle_draws,
            "first_target_e_move": replay.first_target_e_move,
            "target": "B_plus",
        },
        "initial": {
            "O": points["O"],
            "A": points["A"],
            "unit_circle": {"center": points["O"], "radius": 1.0},
        },
        "target": {"id": "B_plus", "point": _point_data(target)},
        "points": points,
        "events": events,
    }


def main() -> int:
    OUTPUT_PATH.write_text(
        json.dumps(build_export(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
