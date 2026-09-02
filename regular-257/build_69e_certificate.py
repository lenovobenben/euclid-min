"""确定性生成公开视频 69E 转写证书。"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from euclid_min.canonical_json import sha256_hex

from cyclotomic_replay import (
    FIELD,
    Circle,
    CyclotomicReplayer,
    Point,
)
from closure_target_audit import ClosureTargetAuditor
from proof_hints import build_proof_hints
from target import is_target_pair


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "construction-69e.json"
PROFILE_HASH_PATH = ROOT / "profile.sha256"
STEPS_PATH = ROOT / "video-69e-steps.csv"


class CertificateBuilder:
    def __init__(self) -> None:
        self.proof_hints = build_proof_hints()
        self.replayer = CyclotomicReplayer()
        target_circle = self.replayer.names["c0"]
        if not isinstance(target_circle, Circle):
            raise AssertionError("c0 必须是圆")
        self.closure_auditor = ClosureTargetAuditor(target_circle)
        self.program: list[dict] = []

    def line(self, name: str, first: str, second: str) -> None:
        self._add({"id": name, "op": "line", "through": [first, second]})

    def circle(self, name: str, center: str, through: str) -> None:
        self._add(
            {
                "id": name,
                "op": "circle",
                "center": center,
                "through": through,
            }
        )

    def bind_expected(self, name: str, first: str, second: str) -> None:
        self.bind_witness(name, first, second, self.proof_hints[name])

    def bind_witness(
        self,
        name: str,
        first: str,
        second: str,
        witness: Point,
    ) -> None:
        index = self.replayer.index_for_witness(first, second, witness)
        entry = {
            "id": name,
            "op": "intersect",
            "objects": [first, second],
            "index": index,
        }
        if os.environ.get("EUCLID_257_BUILD_TRACE") == "1":
            print(
                f"e={self.replayer.e_move} op=intersect id={name}",
                flush=True,
            )
        self.replayer.bind_witness(entry, witness, verified_index=index)
        self.program.append(entry)

    def _add(self, entry: dict) -> None:
        if os.environ.get("EUCLID_257_BUILD_TRACE") == "1":
            print(
                f"e={self.replayer.e_move} op={entry['op']} id={entry['id']}",
                flush=True,
            )
        self.replayer.execute(entry)
        if entry["op"] in ("line", "circle"):
            self.closure_auditor.add_drawable(
                entry["id"],
                self.replayer.names[entry["id"]],
                self.replayer.e_move,
            )
        self.program.append(entry)


def build_program():
    b = CertificateBuilder()

    b.line("a", "C", "B")
    b.bind_expected("M1", "a", "c0")
    b.circle("q", "B", "C")
    b.bind_witness(
        "q_c0_left",
        "q",
        "c0",
        b.proof_hints["q_c0_left"],
    )
    b.bind_witness(
        "q_c0_right",
        "q",
        "c0",
        b.proof_hints["q_c0_right"],
    )
    b.line("d", "q_c0_left", "q_c0_right")
    b.bind_expected("A", "a", "d")
    b.circle("c", "A", "B")
    b.bind_expected("D", "c", "d")
    b.bind_expected("E", "c", "d")
    b.line("BE", "B", "E")
    b.bind_expected("G", "BE", "c0")
    b.line("b", "C", "G")
    b.bind_expected("F", "b", "c0")
    b.line("DM1", "D", "M1")
    b.bind_expected("H", "DM1", "c")
    b.bind_expected("I", "DM1", "b")
    b.line("IE", "I", "E")
    b.bind_expected("K", "IE", "c")
    b.bind_expected("J", "IE", "a")
    b.line("DJ", "D", "J")
    b.bind_expected("L", "DJ", "c")
    b.line("KL", "K", "L")
    b.bind_expected("N", "KL", "BE")
    b.bind_expected("M", "KL", "a")
    b.line("NI", "N", "I")
    b.bind_expected("O", "NI", "a")
    b.line("FO", "F", "O")
    b.bind_expected("A0", "FO", "c")
    b.bind_expected("A1", "FO", "c")
    b.line("BA0", "B", "A0")
    b.bind_expected("R", "BA0", "b")
    b.line("BA1", "B", "A1")
    b.bind_expected("S", "BA1", "b")
    b.line("RM", "R", "M")
    b.bind_expected("B0", "RM", "c")
    b.bind_expected("B2", "RM", "c")
    b.line("SM", "S", "M")
    b.bind_expected("B1", "SM", "c")
    b.bind_expected("B3", "SM", "c")
    b.line("EA1", "E", "A1")
    b.bind_expected("T", "EA1", "a")
    b.line("LB0", "L", "B0")
    b.bind_expected("U", "LB0", "b")
    b.line("UT", "U", "T")
    b.bind_expected("Ca", "UT", "c")
    b.line("EA0", "E", "A0")
    b.bind_expected("V", "EA0", "a")
    b.line("LB1", "L", "B1")
    b.bind_expected("W", "LB1", "b")
    b.line("VW", "V", "W")
    b.bind_expected("Cb", "VW", "c")
    b.line("B0B3", "B0", "B3")
    b.bind_expected("X", "B0B3", "a")
    b.line("RX", "R", "X")
    b.bind_expected("Cc", "RX", "c")
    b.line("B2B3", "B2", "B3")
    b.bind_expected("Y", "B2B3", "a")
    b.line("YS", "Y", "S")
    b.bind_expected("Cd", "YS", "c")
    b.line("HCa", "H", "Ca")
    b.bind_expected("Z", "HCa", "b")
    b.line("ZK", "Z", "K")
    b.bind_expected("H1", "ZK", "a")
    b.line("B1Cc", "B1", "Cc")
    b.bind_expected("I1", "B1Cc", "b")
    b.line("I1H", "I1", "H")
    b.bind_expected("J1", "I1H", "c")
    b.line("BJ1", "B", "J1")
    b.bind_expected("K1", "BJ1", "b")
    b.line("K1H1", "K1", "H1")
    b.bind_expected("Da", "K1H1", "c")
    b.bind_expected("Db", "K1H1", "c")
    b.line("BZ", "B", "Z")
    b.bind_expected("L1", "BZ", "c")
    b.circle("c_M1L1", "M1", "L1")
    b.bind_expected("N1", "c_M1L1", "c")
    b.line("CdN1", "Cd", "N1")
    b.bind_expected("O1", "CdN1", "b")
    b.line("HCb", "H", "Cb")
    b.bind_expected("P1", "HCb", "a")
    b.line("EP1", "E", "P1")
    b.bind_expected("Q1", "EP1", "c")
    b.line("LQ1", "L", "Q1")
    b.bind_expected("R1", "LQ1", "b")
    b.line("R1Cc", "R1", "Cc")
    b.bind_expected("S1", "R1Cc", "c")
    b.line("CdB0", "Cd", "B0")
    b.bind_expected("T1", "CdB0", "b")
    b.line("T1S1", "T1", "S1")
    b.bind_expected("U1", "T1S1", "c")
    b.line("EU1", "E", "U1")
    b.bind_expected("V1", "EU1", "a")
    b.line("V1O1", "V1", "O1")
    b.bind_expected("Dc", "V1O1", "c")
    b.bind_expected("Dd", "V1O1", "c")
    b.line("RS1", "R", "S1")
    b.bind_expected("W1", "RS1", "c")
    b.line("EW1", "E", "W1")
    b.bind_expected("X1", "EW1", "a")
    b.line("X1Z", "X1", "Z")
    b.bind_expected("D0", "X1Z", "c")
    b.bind_expected("D8", "X1Z", "c")
    b.line("BD0", "B", "D0")
    b.bind_expected("Y1", "BD0", "b")
    b.line("GDa", "G", "Da")
    b.bind_expected("Z1", "GDa", "c")
    b.line("DZ1", "D", "Z1")
    b.bind_expected("H2", "DZ1", "a")
    b.line("H2Y1", "H2", "Y1")
    b.bind_expected("E0", "H2Y1", "c")
    b.line("BE0", "B", "E0")
    b.bind_expected("I2", "BE0", "b")
    b.line("DcD0", "Dc", "D0")
    b.bind_expected("J2", "DcD0", "b")
    b.line("AJ2", "A", "J2")
    b.bind_expected("K2", "AJ2", "c")
    b.line("EK2", "E", "K2")
    b.bind_expected("L2", "EK2", "a")
    b.line("L2I2", "L2", "I2")
    b.bind_expected("F0", "L2I2", "c")
    b.line("BD8", "B", "D8")
    b.bind_expected("M2", "BD8", "b")
    b.line("GDb", "G", "Db")
    b.bind_expected("N2", "GDb", "c")
    b.line("DN2", "D", "N2")
    b.bind_expected("O2", "DN2", "a")
    b.line("M2O2", "M2", "O2")
    b.bind_expected("E24", "M2O2", "c")
    b.line("BE24", "B", "E24")
    b.bind_expected("P2", "BE24", "b")
    b.line("D8Dd", "D8", "Dd")
    b.bind_expected("Q2", "D8Dd", "b")
    b.line("AQ2", "A", "Q2")
    b.bind_expected("R2", "AQ2", "c")
    b.line("ER2", "E", "R2")
    b.bind_expected("S2", "ER2", "a")
    b.line("S2P2", "S2", "P2")
    b.bind_expected("F56", "S2P2", "c")
    b.line("BF0", "B", "F0")
    b.bind_expected("T2", "BF0", "b")
    b.line("EF56", "E", "F56")
    b.bind_expected("U2", "EF56", "a")
    b.line("U2T2", "U2", "T2")
    b.bind_expected("G0", "U2T2", "c")
    b.line("BG0", "B", "G0")
    b.bind_expected("V2", "BG0", "b")
    b.circle("target_transfer", "V2", "C")
    b.bind_witness(
        "W2_minus",
        "target_transfer",
        "c0",
        b.proof_hints["W2_minus"],
    )
    b.bind_witness(
        "W2_plus",
        "target_transfer",
        "c0",
        b.proof_hints["W2_plus"],
    )

    return b.program, b.replayer, b.closure_auditor.result()


def _paid_csv_rows() -> list[tuple[int, str, str]]:
    with STEPS_PATH.open(encoding="utf-8", newline="") as handle:
        return [
            (int(row["step"]), row["type"], row["object"])
            for row in csv.DictReader(handle)
        ]


def _target_witnesses(replayer: CyclotomicReplayer) -> list[list[str]]:
    result = replayer.result()
    circle = result.names["c0"]
    if not isinstance(circle, Circle):
        raise AssertionError("c0 必须是圆")
    zeta = FIELD.gen()
    point_items = [
        (name, value)
        for name, value in result.names.items()
        if isinstance(value, Point)
    ]
    witnesses: list[list[str]] = []
    for second_index, (second_name, second) in enumerate(point_items):
        for first_name, first in point_items[:second_index]:
            if is_target_pair(circle, first, second, zeta):
                witnesses.append([first_name, second_name])
    return witnesses


def build_certificate() -> dict:
    program, replayer, closure_audit = build_program()
    result = replayer.result()
    paid_program = [entry for entry in program if entry["op"] != "intersect"]
    paid_csv = _paid_csv_rows()
    paid_from_program = [
        (index, entry["op"], entry["id"])
        for index, entry in enumerate(paid_program, start=1)
    ]
    if paid_from_program != paid_csv:
        raise AssertionError("证书计费步骤与 video-69e-steps.csv 不一致")

    witnesses = _target_witnesses(replayer)
    if witnesses != [["G", "W2_minus"], ["G", "W2_plus"]]:
        raise AssertionError(f"非预期目标点对: {witnesses}")
    if closure_audit.first_target_e_move != 69:
        raise AssertionError(
            f"自动闭包首次目标不是 69E: {closure_audit.first_target_e_move}"
        )
    if closure_audit.duplicate_draws != 0:
        raise AssertionError(
            f"证书含 {closure_audit.duplicate_draws} 个重复作图对象"
        )
    first_bound_target_e_move = min(
        max(
            result.bound_point_e_moves[first],
            result.bound_point_e_moves[second],
        )
        for first, second in witnesses
    )

    construction = {
        "id": "video-69e-transcription",
        "title": "正 257 边形 69E 公视频转写构造",
        "description": (
            "按 video-69e-steps.csv 转写；所有显式交点使用精确字典序索引，"
            "目标为给定圆上的任意一对正 257 边形相邻顶点。"
        ),
        "program": program,
    }
    return {
        "schema": "euclid-min-regular-257-certificate/v2",
        "problem": "regular-257-free-edge",
        "profile": {
            "id": "regular-257-free-edge-e-fixed-v1",
            "sha256": PROFILE_HASH_PATH.read_text(encoding="utf-8").strip(),
        },
        "source": {
            "kind": "public_video_transcription",
            "url": "https://www.bilibili.com/video/BV1CARsYJEVe/",
            "steps_table": "video-69e-steps.csv",
        },
        "construction": construction,
        "assertions": {
            "score": {"metric": "e_move", "e_move": result.e_move},
            "draws": {
                "lines": result.line_draws,
                "circles": result.circle_draws,
                "duplicates": closure_audit.duplicate_draws,
            },
            "target_witnesses": witnesses,
            "first_bound_target_e_move": first_bound_target_e_move,
            "automatic_closure_target_audit": {
                "status": "complete",
                "method": "exact_rotated_chord_carriers",
                "first_target_e_move": closure_audit.first_target_e_move,
            },
            "claim": "verified_construction",
        },
        "software": {
            "producer": {"name": "build_69e_certificate.py", "version": "2"}
        },
        "integrity": {"construction_sha256": sha256_hex(construction)},
    }


def main() -> None:
    certificate = build_certificate()
    OUTPUT_PATH.write_text(
        json.dumps(certificate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote={OUTPUT_PATH}")
    print(f"program_entries={len(certificate['construction']['program'])}")
    print("e_move=69 lines=65 circles=4")
    print(
        "construction_sha256="
        f"{certificate['integrity']['construction_sha256']}"
    )


if __name__ == "__main__":
    main()
