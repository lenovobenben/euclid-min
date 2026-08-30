"""生成 DeTemple 路线经局部精确化简后的 21 E 证书。

原文第 104 页建议用半尺度 Carlyle 圆直接得到 M_{0,2}、M_{1,2}，
并让步骤 (vi) 已有的圆复用于 OY 的中垂线。直接得到这两个中点后，
原步骤 (ii)-(iii) 产生的完整尺度根不再被使用，故一并删除。本转写仍按
`regular-17-e-fixed-v1` 使用 collapsing compass。最后不再搬运单位长度，
而是作 OH_{0,8} 的中垂线，与单位圆直接得到两个目标点。步骤 (vi) 的距离
搬运也由一个经过 Y 的已有点圆替换。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from euclid_min.canonical_json import sha256_hex
from euclid_min.formats import load_profile
from euclid_min.replay import ProgramReplayer
from experiments.build_detemple_1991_baseline import (
    DEFAULT_PROFILE,
    build_program as build_baseline_program,
    circle,
    intersection,
    line,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-improved-converted"
    / "construction.json"
)
DEFAULT_DEPENDENCY_GRAPH_OUTPUT = DEFAULT_OUTPUT.with_name("dependency-graph.json")


def build_program() -> list[dict]:
    """应用论文修改、依赖清理和两个局部精确捷径。"""

    baseline = build_baseline_program()
    first_replaced = next(
        index for index, entry in enumerate(baseline)
        if entry["id"] == "c_Qhalf_A"
    )
    after_replaced = next(
        index for index, entry in enumerate(baseline)
        if entry["id"] == "c_M0_2_Ay"
    )

    half_scaled_step = [
        # Qhalf=Q'=(-1/2,0)。先作 Q'O 的中垂线，得到 (-1/4,0)。
        circle("c_Qhalf_O", "Qhalf", "O"),
        circle("c_O_Qhalf", "O", "Qhalf"),
        intersection("b_Qhalf_low", "c_Qhalf_O", "c_O_Qhalf", 0),
        intersection("b_Qhalf_high", "c_Qhalf_O", "c_O_Qhalf", 1),
        line("bisector_Qhalf_O", "b_Qhalf_low", "b_Qhalf_high"),
        intersection("Qquarter", "bisector_Qhalf_O", "x_axis", 0),

        # x^2 + (1/2)x - 1 = 0 的 Carlyle 圆；两根正是
        # eta_{0,2}/2 与 eta_{1,2}/2，即后续所需的两个圆心。
        circle("c_Qquarter_Ay", "Qquarter", "Ay"),
        intersection("M1_2", "c_Qquarter_Ay", "x_axis", 0),
        intersection("M0_2", "c_Qquarter_Ay", "x_axis", 1),
    ]
    program = (
        baseline[:first_replaced]
        + half_scaled_step
        + baseline[after_replaced:]
    )

    first_replaced = next(
        index for index, entry in enumerate(program)
        if entry["id"] == "copy1_D_Q"
    )
    after_replaced = next(
        index for index, entry in enumerate(program)
        if entry["id"] == "c_M0_4_Ay"
    )
    direct_y_step = [
        # D=(-1/2,1/2) 是已有 bisector_QO 与 c_Qhalf_O 的交点。
        # 以 D 为圆心、过 H1_4 的圆也经过 Y=(0,1+eta_{1,4})，
        # 因为两段的坐标差只交换了次序，平方距离精确相同。
        intersection("direct_y_center", "bisector_QO", "c_Qhalf_O", 1),
        circle("c_direct_y", "direct_y_center", "H1_4"),
        intersection("Y", "y_axis", "c_direct_y", 1),

        # 直接圆不以 O 为圆心，所以补齐 OY 的两个等半径圆，再作中垂线。
        circle("c_O_Y", "O", "Y"),
        circle("c_Y_O", "Y", "O"),
        intersection("b_OY_low", "c_O_Y", "c_Y_O", 0),
        intersection("b_OY_high", "c_O_Y", "c_Y_O", 1),
        line("bisector_O_Y", "b_OY_low", "b_OY_high"),
        line("line_Y_H0_4", "Y", "H0_4"),
        intersection("M0_4", "bisector_O_Y", "line_Y_H0_4", 0),
    ]
    program = (
        program[:first_replaced]
        + direct_y_step
        + program[after_replaced:]
    )

    first_replaced = next(
        index for index, entry in enumerate(program)
        if entry["id"] == "copy2_c_H_O"
    )
    target_chord_step = [
        # H0_8=(2*cos(2*pi/17), 0)。OH0_8 的中垂线是
        # x=cos(2*pi/17)，与单位圆的两个交点正是目标 B_+、B_-。
        circle("target_bisector_c_H_O", "H0_8", "O"),
        circle("target_bisector_c_O_H", "O", "H0_8"),
        intersection(
            "target_bisector_low",
            "target_bisector_c_H_O",
            "target_bisector_c_O_H",
            0,
        ),
        intersection(
            "target_bisector_high",
            "target_bisector_c_H_O",
            "target_bisector_c_O_H",
            1,
        ),
        line(
            "target_chord",
            "target_bisector_low",
            "target_bisector_high",
        ),
    ]
    return program[:first_replaced] + target_chord_step


def build_certificate(profile_path: Path = DEFAULT_PROFILE) -> dict:
    profile = load_profile(profile_path)
    construction = {
        "id": "detemple-1991-carlyle-improved-converted",
        "title": "DeTemple 1991 improved Carlyle construction converted to collapsing compass",
        "description": (
            "Modified DeTemple route using both improvements from page 104, "
            "with the superseded full-scale root branch removed and the final "
            "unit transfer replaced by the perpendicular target chord; the "
            "remaining distance transfer is replaced by an exact local circle "
            "shortcut, and both axes are charged."
        ),
        "program": build_program(),
    }
    replay = ProgramReplayer().replay(construction["program"])
    targets = [target.value for target in replay.targets]
    if not targets:
        raise RuntimeError("生成的改进构造没有精确命中正十七边形目标")

    return {
        "schema": "euclid-min-certificate/v1",
        "problem": profile.data["problem"]["id"],
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "construction": construction,
        "assertions": {
            "score": {"metric": "e_move", "e_move": replay.e_move},
            "targets": targets,
            "claim": "verified_construction",
        },
        "software": {
            "producer": {
                "name": "euclid-min-detemple-improved-generator",
                "version": "1",
            }
        },
        "integrity": {"construction_sha256": sha256_hex(construction)},
    }


def build_dependency_graph(certificate: dict) -> dict:
    """导出与 program 顺序一致、可机器核对的直接依赖 DAG。"""

    nodes = [
        {"id": "O", "op": "initial_point", "cost": 0, "depends_on": []},
        {"id": "A", "op": "initial_point", "cost": 0, "depends_on": []},
        {
            "id": "unit_circle",
            "op": "initial_circle",
            "cost": 0,
            "depends_on": ["O", "A"],
        },
    ]
    e_move = 0
    for entry in certificate["construction"]["program"]:
        operation = entry["op"]
        if operation == "line":
            dependencies = entry["through"]
            cost = 1
        elif operation == "circle":
            dependencies = [entry["center"], entry["through"]]
            cost = 1
        else:
            dependencies = entry["objects"]
            cost = 0
        e_move += cost
        nodes.append(
            {
                "id": entry["id"],
                "op": operation,
                "cost": cost,
                "e_move_after": e_move,
                "depends_on": dependencies,
            }
        )
    return {
        "schema": "euclid-min-dependency-graph/v1",
        "construction_id": certificate["construction"]["id"],
        "construction_sha256": certificate["integrity"]["construction_sha256"],
        "profile": certificate["profile"],
        "total_e_move": e_move,
        "nodes": nodes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--dependency-graph-output",
        type=Path,
        default=DEFAULT_DEPENDENCY_GRAPH_OUTPUT,
    )
    args = parser.parse_args()

    certificate = build_certificate(args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(certificate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    dependency_graph = build_dependency_graph(certificate)
    args.dependency_graph_output.parent.mkdir(parents=True, exist_ok=True)
    args.dependency_graph_output.write_text(
        json.dumps(dependency_graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    print(args.dependency_graph_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
