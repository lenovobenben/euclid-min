"""生成 DeTemple 1991 Carlyle 十七边形构造的 collapsing-compass 转写。

原文从单位圆和两条坐标轴开始，并允许现代 non-collapsing compass 的距离
搬运。本转写从 `regular-17-e-fixed-v1` 的 O、A 和单位圆开始：坐标轴计费，
两次距离搬运按 Euclid I.2 风格展开为基础圆规和直尺操作。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from euclid_min.canonical_json import sha256_hex
from euclid_min.formats import load_profile
from euclid_min.replay import ProgramReplayer


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPOSITORY_ROOT / "profiles" / "regular-17-e-fixed-v1.yaml"
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "baselines"
    / "regular-17"
    / "detemple-1991-carlyle-converted"
    / "construction.json"
)


def line(entry_id: str, first: str, second: str) -> dict:
    return {"id": entry_id, "op": "line", "through": [first, second]}


def circle(entry_id: str, center: str, through: str) -> dict:
    return {
        "id": entry_id,
        "op": "circle",
        "center": center,
        "through": through,
    }


def intersection(
    entry_id: str,
    first: str,
    second: str,
    index: int,
) -> dict:
    return {
        "id": entry_id,
        "op": "intersect",
        "objects": [first, second],
        "index": index,
    }


def build_program() -> list[dict]:
    return [
        # 从免费 O、A 和单位圆构造 x 轴、Q=(-1,0) 以及 y 轴上的 Ay=(0,1)。
        line("x_axis", "O", "A"),
        intersection("Q", "x_axis", "unit_circle", 0),
        circle("c_A_Q", "A", "Q"),
        circle("c_Q_A", "Q", "A"),
        intersection("y_axis_low", "c_A_Q", "c_Q_A", 0),
        intersection("y_axis_high", "c_A_Q", "c_Q_A", 1),
        line("y_axis", "y_axis_low", "y_axis_high"),
        intersection("Ay", "y_axis", "unit_circle", 1),

        # DeTemple 步骤 (i)：QO 的垂直平分线及 Qhalf=(-1/2,0)。
        circle("c_Q_O", "Q", "O"),
        intersection("eq_QO_low", "c_Q_O", "unit_circle", 0),
        intersection("eq_QO_high", "c_Q_O", "unit_circle", 1),
        line("bisector_QO", "eq_QO_low", "eq_QO_high"),
        intersection("Qhalf", "bisector_QO", "x_axis", 0),

        # 步骤 (ii)-(iii)：第一个 Carlyle 圆，得到 eta_{0,2} 与 eta_{1,2}。
        circle("c_Qhalf_A", "Qhalf", "A"),
        intersection("M0", "c_Qhalf_A", "bisector_QO", 0),
        circle("c_M0_Ay", "M0", "Ay"),
        intersection("H1_2", "c_M0_Ay", "x_axis", 0),
        intersection("H0_2", "c_M0_Ay", "x_axis", 1),

        # 步骤 (iv)：分别构造 OH0_2、OH1_2 的中点。
        circle("c_O_H0_2", "O", "H0_2"),
        circle("c_H0_2_O", "H0_2", "O"),
        intersection("b_H0_low", "c_O_H0_2", "c_H0_2_O", 0),
        intersection("b_H0_high", "c_O_H0_2", "c_H0_2_O", 1),
        line("bisector_O_H0_2", "b_H0_low", "b_H0_high"),
        intersection("M0_2", "bisector_O_H0_2", "x_axis", 0),
        circle("c_O_H1_2", "O", "H1_2"),
        circle("c_H1_2_O", "H1_2", "O"),
        intersection("b_H1_low", "c_O_H1_2", "c_H1_2_O", 0),
        intersection("b_H1_high", "c_O_H1_2", "c_H1_2_O", 1),
        line("bisector_O_H1_2", "b_H1_low", "b_H1_high"),
        intersection("M1_2", "bisector_O_H1_2", "x_axis", 0),

        # 步骤 (v)：两个 Carlyle 圆，保留所需的 eta_{0,4} 与 eta_{1,4}。
        circle("c_M0_2_Ay", "M0_2", "Ay"),
        intersection("H0_4", "c_M0_2_Ay", "x_axis", 1),
        circle("c_M1_2_Ay", "M1_2", "Ay"),
        intersection("H1_4", "c_M1_2_Ay", "x_axis", 1),

        # 步骤 (vi)：把 QH1_4 搬运到 O，得到 Y=(0,1+eta_{1,4})。
        # 使用 eq_QO_high 作为 OQ 上的等边三角形顶点，按 Euclid I.2 展开。
        line("copy1_D_Q", "eq_QO_high", "Q"),
        line("copy1_D_O", "eq_QO_high", "O"),
        circle("copy1_c_Q_H1_4", "Q", "H1_4"),
        intersection("copy1_G", "copy1_D_Q", "copy1_c_Q_H1_4", 0),
        circle("copy1_c_D_G", "eq_QO_high", "copy1_G"),
        intersection("copy1_L", "copy1_D_O", "copy1_c_D_G", 1),
        circle("c_O_QH1_4", "O", "copy1_L"),
        intersection("Y", "c_O_QH1_4", "y_axis", 1),

        # 步骤 (vii)-(viii)：YH0_4 及其中点 M0_4。
        line("line_Y_H0_4", "Y", "H0_4"),
        circle("c_Y_H0_4", "Y", "H0_4"),
        circle("c_H0_4_Y", "H0_4", "Y"),
        intersection("b_YH_low", "c_Y_H0_4", "c_H0_4_Y", 0),
        intersection("b_YH_high", "c_Y_H0_4", "c_H0_4_Y", 1),
        line("bisector_Y_H0_4", "b_YH_low", "b_YH_high"),
        intersection("M0_4", "line_Y_H0_4", "bisector_Y_H0_4", 0),

        # 步骤 (ix)：最后一个 Carlyle 圆，H0_8=2*cos(2*pi/17)。
        circle("c_M0_4_Ay", "M0_4", "Ay"),
        intersection("H0_8", "c_M0_4_Ay", "x_axis", 1),

        # 步骤 (x)：把单位长度 OA 搬运到 H0_8，再与单位圆相交。
        circle("copy2_c_H_O", "H0_8", "O"),
        circle("copy2_c_O_H", "O", "H0_8"),
        intersection("copy2_D", "copy2_c_H_O", "copy2_c_O_H", 1),
        line("copy2_D_O", "copy2_D", "O"),
        line("copy2_D_H", "copy2_D", "H0_8"),
        intersection("copy2_G", "copy2_D_O", "unit_circle", 0),
        circle("copy2_c_D_G", "copy2_D", "copy2_G"),
        intersection("copy2_L", "copy2_D_H", "copy2_c_D_G", 1),
        circle("target_circle", "H0_8", "copy2_L"),
    ]


def build_certificate(profile_path: Path = DEFAULT_PROFILE) -> dict:
    profile = load_profile(profile_path)
    construction = {
        "id": "detemple-1991-carlyle-converted",
        "title": "DeTemple 1991 Carlyle construction converted to collapsing compass",
        "description": (
            "Unmodified ten-step DeTemple construction with coordinate axes charged "
            "and both non-collapsing distance transfers expanded."
        ),
        "program": build_program(),
    }
    replay = ProgramReplayer().replay(construction["program"])
    targets = [target.value for target in replay.targets]
    if not targets:
        raise RuntimeError("生成的 baseline 没有精确命中正十七边形目标")

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
                "name": "euclid-min-detemple-baseline-generator",
                "version": "1",
            }
        },
        "integrity": {"construction_sha256": sha256_hex(construction)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    certificate = build_certificate(args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(certificate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
