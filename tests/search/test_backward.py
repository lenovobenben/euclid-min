from __future__ import annotations

import json
import unittest
from pathlib import Path

from euclid_min.search import SearchNode
from euclid_min.search.backward import (
    generate_regular17_terminal_candidates,
    is_regular17_terminal_step,
    regular17_targets_on_step,
)
from euclid_min.search.export import steps_from_program
from euclid_min.target import TargetName


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMPROVED_CERTIFICATE = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)


class BackwardTerminalConstraintTests(unittest.TestCase):
    def test_initial_state_has_no_one_move_terminal_candidate(self):
        candidates = generate_regular17_terminal_candidates(
            SearchNode.initial().state
        )
        self.assertEqual(candidates, ())

    def test_known_19e_path_first_gets_target_on_its_last_step(self):
        certificate = json.loads(IMPROVED_CERTIFICATE.read_text(encoding="utf-8"))
        steps = steps_from_program(certificate["construction"]["program"])

        self.assertEqual(len(steps), 19)
        self.assertTrue(all(not is_regular17_terminal_step(step) for step in steps[:-1]))
        self.assertTrue(is_regular17_terminal_step(steps[-1]))
        self.assertEqual(
            regular17_targets_on_step(steps[-1]),
            (TargetName.B_PLUS,),
        )


if __name__ == "__main__":
    unittest.main()
