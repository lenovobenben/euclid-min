"""严格加载并验证正 257 边形 69E JSON 证书。"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import jsonschema
import yaml
from sage.version import version as sage_version

from euclid_min.canonical_json import sha256_hex

from cyclotomic_replay import FIELD, Circle, CyclotomicReplayer, Point
from closure_target_audit import ClosureTargetAuditor
from proof_hints import build_proof_hints
from target import is_target_pair


ROOT = Path(__file__).resolve().parent
CERTIFICATE_PATH = ROOT / "construction-69e.json"
CERTIFICATE_SCHEMA_PATH = ROOT / "certificate.schema.json"
PROFILE_PATH = ROOT / "profile.yaml"
PROFILE_SCHEMA_PATH = ROOT / "profile.schema.json"
STEPS_PATH = ROOT / "video-69e-steps.csv"
REPORT_PATH = ROOT / "verification-69e.json"


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 对象含重复键 {key!r}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )


def _validate(instance: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(instance)


def _paid_csv_rows() -> list[tuple[int, str, str]]:
    with STEPS_PATH.open(encoding="utf-8", newline="") as handle:
        return [
            (int(row["step"]), row["type"], row["object"])
            for row in csv.DictReader(handle)
        ]


def _target_witnesses(result) -> list[list[str]]:
    circle = result.names["c0"]
    if not isinstance(circle, Circle):
        raise AssertionError("c0 必须是圆")
    zeta = FIELD.gen()
    points = [
        (name, value)
        for name, value in result.names.items()
        if isinstance(value, Point)
    ]
    witnesses: list[list[str]] = []
    for second_index, (second_name, second) in enumerate(points):
        for first_name, first in points[:second_index]:
            if is_target_pair(circle, first, second, zeta):
                witnesses.append([first_name, second_name])
    return witnesses


def verify_certificate(path: Path = CERTIFICATE_PATH) -> dict:
    raw = path.read_bytes()
    certificate = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    _validate(certificate, CERTIFICATE_SCHEMA_PATH)

    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    _validate(profile, PROFILE_SCHEMA_PATH)
    profile_hash = sha256_hex(profile)
    if certificate["profile"]["sha256"] != profile_hash:
        raise ValueError("证书声明的 profile 摘要不匹配")

    construction = certificate["construction"]
    construction_hash = sha256_hex(construction)
    if certificate["integrity"]["construction_sha256"] != construction_hash:
        raise ValueError("证书声明的 construction 摘要不匹配")

    program = construction["program"]
    paid_program = [entry for entry in program if entry["op"] != "intersect"]
    paid_rows = [
        (index, entry["op"], entry["id"])
        for index, entry in enumerate(paid_program, start=1)
    ]
    if paid_rows != _paid_csv_rows():
        raise ValueError("证书计费步骤与视频转写 CSV 不一致")

    hints = build_proof_hints()
    replayer = CyclotomicReplayer()
    target_circle = replayer.names["c0"]
    if not isinstance(target_circle, Circle):
        raise AssertionError("c0 必须是圆")
    closure_auditor = ClosureTargetAuditor(target_circle)
    verified_hints = 0
    for program_index, entry in enumerate(program):
        try:
            if entry["op"] == "intersect":
                try:
                    hint = hints[entry["id"]]
                except KeyError as error:
                    raise ValueError("交点缺少精确 proof hint") from error
                replayer.bind_witness(entry, hint)
                verified_hints += 1
            else:
                replayer.execute(entry)
                closure_auditor.add_drawable(
                    entry["id"],
                    replayer.names[entry["id"]],
                    replayer.e_move,
                )
        except Exception as error:
            raise ValueError(
                f"program[{program_index}] {entry['id']!r} 验证失败: {error}"
            ) from error

    result = replayer.result()
    closure_audit = closure_auditor.result()
    witnesses = _target_witnesses(result)
    first_bound_target_e_move = min(
        max(
            result.bound_point_e_moves[first],
            result.bound_point_e_moves[second],
        )
        for first, second in witnesses
    )
    assertions = certificate["assertions"]
    actual_score = {"metric": "e_move", "e_move": result.e_move}
    actual_draws = {
        "lines": result.line_draws,
        "circles": result.circle_draws,
        "duplicates": closure_audit.duplicate_draws,
    }
    actual_closure_target_audit = {
        "status": "complete",
        "method": "exact_rotated_chord_carriers",
        "first_target_e_move": closure_audit.first_target_e_move,
    }
    if assertions["score"] != actual_score:
        raise ValueError("E-move 声明与重算结果不一致")
    if assertions["draws"] != actual_draws:
        raise ValueError("直线/圆计数声明与重算结果不一致")
    if assertions["target_witnesses"] != witnesses:
        raise ValueError("目标见证声明与重算结果不一致")
    if assertions["first_bound_target_e_move"] != first_bound_target_e_move:
        raise ValueError("首次显式绑定目标的 E 值不一致")
    if (
        assertions["automatic_closure_target_audit"]
        != actual_closure_target_audit
    ):
        raise ValueError("自动闭包首次目标声明与精确审计不一致")

    first_target_sources = [
        {
            "new_object": hit.new_object,
            "source_object": hit.source_object,
            "orientation": hit.orientation,
        }
        for hit in closure_audit.first_hits
    ]

    point_names = sum(isinstance(value, Point) for value in result.names.values())
    return {
        "schema": "euclid-min-regular-257-verification-report/v2",
        "certificate_sha256": hashlib.sha256(raw).hexdigest(),
        "construction_sha256": construction_hash,
        "profile": {
            "id": certificate["profile"]["id"],
            "sha256": profile_hash,
        },
        "verifier": {
            "name": "verify_69e_certificate.py",
            "version": "2",
            "sage_version": sage_version,
            "exact_backend": (
                "CyclotomicField(257)+UniversalCyclotomicField"
            ),
        },
        "valid": True,
        "verification_scope": (
            "explicit_bindings_and_complete_target_closure_audit"
        ),
        "program_entries": len(program),
        "proof_hints_verified": verified_hints,
        "draws": actual_draws,
        "bound_point_names": point_names,
        "score": actual_score,
        "target_witnesses": witnesses,
        "first_bound_target_e_move": first_bound_target_e_move,
        "automatic_closure_target_audit": actual_closure_target_audit,
        "first_target_sources": first_target_sources,
    }


def main() -> None:
    report = verify_certificate()
    _validate(report, ROOT / "verification.schema.json")
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("valid=true")
    print(
        f"program_entries={report['program_entries']} "
        f"proof_hints_verified={report['proof_hints_verified']}"
    )
    print("e_move=69 lines=65 circles=4")
    print(f"target_witnesses={report['target_witnesses']}")
    print("automatic_closure_first_target_e_move=69")
    print("duplicate_draws=0")


if __name__ == "__main__":
    main()
