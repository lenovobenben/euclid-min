"""从公开视频恢复的正 257 边形 69E 构造测试。"""

from __future__ import annotations

import unittest

from euclid_min.regular_257_video_69e import verify


class Regular257Video69ETests(unittest.TestCase):
    def test_exact_incidence_and_target_axis(self) -> None:
        replay, g0, target_axis = verify()

        self.assertEqual(len(replay.steps), 69)
        self.assertEqual(replay.lines, 65)
        self.assertEqual(replay.circles, 4)
        self.assertEqual(target_axis.b, 0)
        self.assertEqual(-target_axis.c / target_axis.a, g0)


if __name__ == "__main__":
    unittest.main()
