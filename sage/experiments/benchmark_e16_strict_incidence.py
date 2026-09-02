"""测量单个 E16 首步上的严格区间目标入射生成器。"""

from __future__ import annotations

import argparse
import faulthandler
import json
from time import perf_counter

from euclid_min.search.candidates import generate_candidates
from euclid_min.search.export import node_from_steps, steps_from_program
from euclid_min.search.incidence import (
    generate_terminal_candidates_with_deferred_incidence,
    generate_terminal_candidates_using_new_points_strict,
    new_points_on_existing_drawable,
)
from experiments.build_regular17_geometry_algebra_ir import CERTIFICATE_PATH
from experiments.search_e16_two_step_target_extension import (
    _apply_precursor,
    _program_prefix,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_index", type=int)
    parser.add_argument("--dump-after-seconds", type=float)
    parser.add_argument("--defer", action="store_true")
    args = parser.parse_args()
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    prefix = _program_prefix(certificate["construction"]["program"], 16)
    state = node_from_steps(steps_from_program(prefix)).state
    candidates = generate_candidates(state)
    precursor = candidates[args.candidate_index]
    child, addition = _apply_precursor(state, precursor)
    if args.dump_after_seconds is not None:
        faulthandler.dump_traceback_later(
            args.dump_after_seconds,
            repeat=False,
            exit=True,
        )
    started = perf_counter()
    if args.defer:
        unit_points = new_points_on_existing_drawable(
            state,
            addition,
            state.circles[0],
        )
        generated = generate_terminal_candidates_with_deferred_incidence(
            child,
            addition.new_points,
            new_unit_circle_points=unit_points,
        )
        terminals = generated.candidates
        audit = generated.audit
        deferred = [item.as_dict() for item in generated.deferred]
    else:
        terminals, audit = generate_terminal_candidates_using_new_points_strict(
            child, addition.new_points
        )
        deferred = []
    if args.dump_after_seconds is not None:
        faulthandler.cancel_dump_traceback_later()
    print(
        json.dumps(
            {
                "candidate_index": args.candidate_index,
                "precursor_operation": precursor.op,
                "new_points": len(addition.new_points),
                "terminal_candidates": len(terminals),
                "deferred": deferred,
                "audit": audit.as_dict(),
                "elapsed_seconds": perf_counter() - started,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
