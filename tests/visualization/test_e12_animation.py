from __future__ import annotations

import configparser
import importlib.util
import json
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "animations/e12"
SPEC = importlib.util.spec_from_file_location("e12_export", HERE / "export_geometry.py")
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class TwelveMoveAnimationTests(unittest.TestCase):
    def test_snapshot_regenerates_deterministically(self):
        committed = json.loads((HERE / "geometry.json").read_text(encoding="utf-8"))
        self.assertEqual(EXPORT.build_export(), committed)
        self.assertEqual(committed["verified_result"], {
            "e_move": 12, "line_draws": 3, "circle_draws": 9,
            "first_target_e_move": 12, "targets": ["B_plus", "B_minus"],
        })

    def test_snapshot_uses_mathematical_coordinates_and_early_point_birth(self):
        data = EXPORT.build_export()
        self.assertEqual(data["points"]["ggb_H"]["birth"], 2)
        self.assertGreater(Decimal(data["points"]["ggb_Q"]["xy"][1]), 0)
        self.assertLess(Decimal(data["points"]["ggb_R"]["xy"][1]), 0)
        self.assertEqual([step["e"] for step in data["steps"]], list(range(1, 13)))
        for step in data["steps"]:
            for point_id in step["refs"]:
                self.assertLess(data["points"][point_id]["birth"], step["e"])

    def test_stale_upstream_report_is_rejected(self):
        report = json.loads(EXPORT.WEB_REPORT.read_text(encoding="utf-8"))
        report["geometry_sha256"] = "0" * 64
        with patch.object(Path, "read_text", return_value=json.dumps(report)):
            with self.assertRaisesRegex(ValueError, "Web geometry changed"):
                EXPORT.build_export()

    def test_release_profile_is_4k_at_thirty_frames(self):
        parser = configparser.ConfigParser()
        parser.read(HERE / "manim.cfg", encoding="utf-8")
        self.assertEqual(parser["CLI"].getint("pixel_width"), 3840)
        self.assertEqual(parser["CLI"].getint("pixel_height"), 2160)
        self.assertEqual(parser["CLI"].getint("frame_rate"), 30)
        self.assertEqual(parser["CLI"]["media_dir"], "animations/e12/media")
