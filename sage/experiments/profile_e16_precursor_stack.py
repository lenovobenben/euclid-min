"""对单个 E16 两步首步做限时堆栈采样，定位精确算术热点。"""

from __future__ import annotations

import argparse
import faulthandler
import json

from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import node_from_steps, steps_from_program
from experiments.build_regular17_geometry_algebra_ir import CERTIFICATE_PATH
from experiments.search_e16_two_step_target_extension import (
    _program_prefix,
    _search_precursor,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_index", type=int)
    parser.add_argument("--dump-after-seconds", type=float, default=20.0)
    args = parser.parse_args()
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    prefix = _program_prefix(certificate["construction"]["program"], 16)
    state = node_from_steps(steps_from_program(prefix)).state
    candidates = generate_candidates(state)
    if not 0 <= args.candidate_index < len(candidates):
        parser.error("candidate_index 越界")
    faulthandler.dump_traceback_later(
        args.dump_after_seconds,
        repeat=False,
        exit=True,
    )
    result = _search_precursor(
        state,
        candidates[args.candidate_index],
        args.candidate_index,
    )
    faulthandler.cancel_dump_traceback_later()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
