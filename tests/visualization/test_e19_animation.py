from __future__ import annotations

import configparser
import json
import unittest
from pathlib import Path

from euclid_min.geometry import Circle, Line, Point
from euclid_min.replay import ProgramReplayer


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CERTIFICATE_PATH = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)
GEOMETRY_PATH = REPOSITORY_ROOT / "animations" / "e19" / "geometry.json"
MANIM_CONFIG_PATH = REPOSITORY_ROOT / "animations" / "e19" / "manim.cfg"


class E19AnimationDataTests(unittest.TestCase):
    def test_release_render_profile_is_4k_30fps(self) -> None:
        parser = configparser.ConfigParser()
        parser.read(MANIM_CONFIG_PATH, encoding="utf-8")
        cli = parser["CLI"]

        self.assertEqual(cli.getint("pixel_width"), 3840)
        self.assertEqual(cli.getint("pixel_height"), 2160)
        self.assertEqual(cli.getint("frame_rate"), 30)

    def test_every_draw_has_two_exported_reference_points(self) -> None:
        exported = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
        points = exported["points"]

        for event in exported["events"]:
            if event["kind"] != "draw":
                continue
            if event["op"] == "line":
                references = event["through"]
            else:
                references = [event["center"], event["through"]]

            self.assertEqual(len(references), 2, event["id"])
            for point_id in references:
                self.assertIn(point_id, points, event["id"])

    def test_export_matches_verified_certificate_replay(self) -> None:
        certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
        exported = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
        program = certificate["construction"]["program"]
        replay = ProgramReplayer().replay(program)

        self.assertEqual(exported["schema"], "euclid-min-manim-e19/v1")
        self.assertEqual(
            exported["source"]["construction_sha256"],
            certificate["integrity"]["construction_sha256"],
        )
        self.assertEqual(replay.e_move, 19)
        self.assertEqual(replay.first_target_e_move, 19)
        self.assertEqual(exported["verified_result"]["line_draws"], 8)
        self.assertEqual(exported["verified_result"]["circle_draws"], 11)

        self.assertEqual(len(exported["events"]), len(program))
        e_move = 0
        for entry, event in zip(program, exported["events"], strict=True):
            self.assertEqual(event["id"], entry["id"])
            value = replay.names[entry["id"]]
            if entry["op"] == "intersect":
                self.assertEqual(event["kind"], "intersection")
                self.assertIsInstance(value, Point)
                self.assertAlmostEqual(event["point"][0], float(value.x), places=14)
                self.assertAlmostEqual(event["point"][1], float(value.y), places=14)
                continue

            e_move += 1
            self.assertEqual(event["kind"], "draw")
            self.assertEqual(event["e_move"], e_move)
            if isinstance(value, Line):
                self.assertEqual(event["op"], "line")
                self.assertAlmostEqual(event["geometry"]["a"], float(value.a), places=14)
                self.assertAlmostEqual(event["geometry"]["b"], float(value.b), places=14)
                self.assertAlmostEqual(event["geometry"]["c"], float(value.c), places=14)
            else:
                self.assertIsInstance(value, Circle)
                self.assertEqual(event["op"], "circle")
                self.assertAlmostEqual(
                    event["geometry"]["radius"],
                    float(value.radius_squared.sqrt()),
                    places=14,
                )

        self.assertEqual(e_move, 19)
        self.assertEqual(exported["events"][-1]["id"], "target_line")


if __name__ == "__main__":
    unittest.main()
