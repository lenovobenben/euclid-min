"""生成 DeTemple 路线经局部精确化简后的 19 E 证书。

原文第 104 页建议用半尺度 Carlyle 圆直接得到 M_{0,2}、M_{1,2}，
并让步骤 (vi) 已有的圆复用于 OY 的中垂线。直接得到这两个中点后，
原步骤 (ii)-(iii) 产生的完整尺度根不再被使用，故一并删除。本转写仍按
`regular-17-e-fixed-v1` 使用 collapsing compass。最后不再搬运单位长度，
而是利用另一个 Carlyle 根和已有圆作一条目标线。步骤 (vi) 的距离
搬运也由一个经过 Y 的已有点圆替换；M_{0,4} 则由三条辅助直线定位。
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
    """应用论文修改、依赖清理和局部精确窗口替换。"""

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

        # 两步局部窗口搜索找到一条更短的 M0_4 定位路线。R=(1/2,0)，
        # V 是半尺度 Carlyle 圆在 x=-1/4 上的下交点。直线 M0_2 V
        # 与 x=-1/2 相交于 N，再连 NR；所得直线精确经过 M0_4。
        intersection("positive_half", "x_axis", "c_O_Qhalf", 1),
        intersection(
            "scaled_circle_low",
            "bisector_Qhalf_O",
            "c_Qquarter_Ay",
            0,
        ),
        line("m_center_helper_1", "M0_2", "scaled_circle_low"),
        intersection(
            "m_center_helper_point",
            "m_center_helper_1",
            "bisector_QO",
            0,
        ),
        line("m_center_helper_2", "m_center_helper_point", "positive_half"),
        line("line_Y_H0_4", "Y", "H0_4"),
        intersection("M0_4", "m_center_helper_2", "line_Y_H0_4", 0),
    ]
    program = (
        program[:first_replaced]
        + direct_y_step
        + program[after_replaced:]
    )

    first_replaced = next(
        index for index, entry in enumerate(program)
        if entry["id"] == "H0_8"
    )
    target_line_step = [
        # 取最后 Carlyle 圆在横轴上的另一个根 H4_8。以 O 为圆心过
        # H4_8 的圆与已有 c_Q_O 的上交点为 P；精确关联搜索确认 QP
        # 经过 B_+，故与单位圆直接给出一个合规目标。
        intersection(
            "H4_8",
            "c_M0_4_Ay",
            "x_axis",
            0,
        ),
        circle("target_helper_circle", "O", "H4_8"),
        intersection(
            "target_helper_point",
            "target_helper_circle",
            "c_Q_O",
            1,
        ),
        line("target_line", "Q", "target_helper_point"),
    ]
    return program[:first_replaced] + target_line_step


def build_certificate(profile_path: Path = DEFAULT_PROFILE) -> dict:
    profile = load_profile(profile_path)
    construction = {
        "id": "detemple-1991-carlyle-improved-converted",
        "title": "DeTemple 1991 improved Carlyle construction converted to collapsing compass",
        "description": (
            "Modified DeTemple route using both improvements from page 104, "
            "with the superseded full-scale root branch removed and the final "
            "unit transfer replaced by a two-move exact target line; the "
            "remaining distance transfer is replaced by an exact local circle "
            "shortcut, the last Carlyle center is located by a three-line "
            "exact window replacement, and both axes are charged."
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
