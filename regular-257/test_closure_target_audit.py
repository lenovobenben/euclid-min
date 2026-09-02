"""正 257 边形自动闭包目标审计测试。"""

from __future__ import annotations

import unittest

from closure_target_audit import (
    COSINE,
    SINE_SQUARED,
    ClosureTargetAuditor,
    Quadratic,
)
from cyclotomic_replay import Circle, Line, Point


class ClosureTargetAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target_circle = Circle(Point(0, -1), 4)

    def test_quadratic_sine_relation_is_exact(self) -> None:
        sine = Quadratic(0, 1)
        self.assertEqual(sine * sine, Quadratic(SINE_SQUARED))

    def test_initial_point_adjacency_is_detected_without_roots(self) -> None:
        auditor = ClosureTargetAuditor(self.target_circle)
        # 中心坐标中 y=2*cos(theta)，同时承载 B 的两个相邻点。
        adjacent_chord = Line(0, 1, 1 - 2 * COSINE)
        auditor.add_drawable("adjacent_chord", adjacent_chord, 1)
        result = auditor.result()
        self.assertEqual(result.first_target_e_move, 1)
        self.assertEqual(
            {hit.source_object for hit in result.first_hits},
            {"B"},
        )

    def test_non_target_diameter_and_duplicate_are_audited(self) -> None:
        auditor = ClosureTargetAuditor(self.target_circle)
        diameter = Line(0, 1, 1)
        self.assertTrue(auditor.add_drawable("diameter", diameter, 1))
        self.assertFalse(auditor.add_drawable("diameter_again", diameter, 2))
        result = auditor.result()
        self.assertIsNone(result.first_target_e_move)
        self.assertEqual(result.distinct_lines, 1)
        self.assertEqual(result.duplicate_draws, 1)


if __name__ == "__main__":
    unittest.main()
