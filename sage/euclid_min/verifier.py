"""完整构造证书验证和独立报告。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sage.version import version as sage_version

from .errors import VerificationError
from .formats import (
    LoadedCertificate,
    LoadedProfile,
    construction_sha256,
    load_certificate,
    load_profile,
)
from .replay import ProgramReplayer, ReplayResult
from .version import __version__


VERIFIER_NAME = "euclid-min-sage-verifier"
SUPPORTED_CLAIM = "verified_construction"


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """可序列化的 verifier 运行结果。"""

    data: dict[str, Any]

    @property
    def valid(self) -> bool:
        return bool(self.data["valid"])

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)


def verify_files(
    certificate_path: str | Path,
    profile_path: str | Path,
) -> VerificationReport:
    """从文件严格加载并验证证书；预期失败也返回报告。"""

    loaded_certificate: LoadedCertificate | None = None
    loaded_profile: LoadedProfile | None = None
    construction_digest: str | None = None
    try:
        loaded_certificate = load_certificate(certificate_path)
        loaded_profile = load_profile(profile_path)
        construction_digest = construction_sha256(
            loaded_certificate.data["construction"]
        )
        return verify_loaded(
            loaded_certificate,
            loaded_profile,
            construction_digest=construction_digest,
        )
    except VerificationError as error:
        certificate_digest = (
            loaded_certificate.file_sha256
            if loaded_certificate is not None
            else error.details.get("certificate_sha256")
        )
        return _failure_report(
            error,
            certificate_sha256=certificate_digest,
            profile=loaded_profile,
            construction_digest=construction_digest,
        )


def verify_loaded(
    certificate: LoadedCertificate,
    profile: LoadedProfile,
    *,
    construction_digest: str | None = None,
) -> VerificationReport:
    """验证已经通过结构校验的数据模型。"""

    certificate_data = certificate.data
    profile_data = profile.data

    if certificate_data["problem"] != profile_data["problem"]["id"]:
        raise VerificationError(
            "problem_id_mismatch",
            "证书 problem 与 profile problem 不一致",
        )
    if certificate_data["profile"]["id"] != profile_data["id"]:
        raise VerificationError(
            "profile_id_mismatch",
            "证书 profile ID 与加载的 profile 不一致",
        )
    if certificate_data["profile"]["sha256"] != profile.sha256:
        raise VerificationError(
            "profile_hash_mismatch",
            "证书声明的 profile SHA-256 与重算值不一致",
            details={
                "asserted": certificate_data["profile"]["sha256"],
                "actual": profile.sha256,
            },
        )

    actual_construction_digest = construction_digest or construction_sha256(
        certificate_data["construction"]
    )
    asserted_construction_digest = certificate_data["integrity"][
        "construction_sha256"
    ]
    if asserted_construction_digest != actual_construction_digest:
        raise VerificationError(
            "construction_hash_mismatch",
            "证书声明的 construction SHA-256 与重算值不一致",
            details={
                "asserted": asserted_construction_digest,
                "actual": actual_construction_digest,
            },
        )

    replay = ProgramReplayer().replay(
        certificate_data["construction"]["program"]
    )
    asserted_e_move = certificate_data["assertions"]["score"]["e_move"]
    if asserted_e_move != replay.e_move:
        raise VerificationError(
            "score_assertion_mismatch",
            "证书声明的 E-score 与重算值不一致",
            details={"asserted": asserted_e_move, "actual": replay.e_move},
        )

    actual_targets = [target.value for target in replay.targets]
    if not actual_targets:
        raise VerificationError(
            "target_not_reached",
            "构造程序结束时没有出现任一正十七边形相邻目标点",
            details={
                "actual_targets": [],
                "e_move": replay.e_move,
            },
        )

    asserted_targets = certificate_data["assertions"]["targets"]
    if set(asserted_targets) != set(actual_targets):
        raise VerificationError(
            "target_assertion_mismatch",
            "证书声明的目标集合与精确重算结果不一致",
            details={"asserted": asserted_targets, "actual": actual_targets},
        )

    return _success_report(
        certificate,
        profile,
        actual_construction_digest,
        replay,
    )


def _success_report(
    certificate: LoadedCertificate,
    profile: LoadedProfile,
    construction_digest: str,
    replay: ReplayResult,
) -> VerificationReport:
    certificate_data = certificate.data
    data = _base_report()
    data.update(
        {
            "certificate_sha256": certificate.file_sha256,
            "construction_sha256": construction_digest,
            "profile": {"id": profile.data["id"], "sha256": profile.sha256},
            "valid": True,
            "draw_operations": {
                "lines": replay.line_draws,
                "circles": replay.circle_draws,
                "total": replay.e_move,
            },
            "distinct_objects": {
                "lines": len(replay.state.lines),
                "circles": len(replay.state.circles),
            },
            "bound_points": len(replay.state.points),
            "closure_strategy": "implicit_exact",
            "duplicate_draws": replay.duplicate_draws,
            "score": {"metric": "e_move", "e_move": replay.e_move},
            "targets": [target.value for target in replay.targets],
            "first_target_program_index": replay.first_target_program_index,
            "first_target_e_move": replay.first_target_e_move,
            "requested_claim": certificate_data["assertions"]["claim"],
            "supported_claim": SUPPORTED_CLAIM,
        }
    )
    return VerificationReport(data)


def _failure_report(
    error: VerificationError,
    *,
    certificate_sha256: str | None = None,
    profile: LoadedProfile | None = None,
    construction_digest: str | None = None,
) -> VerificationReport:
    data = _base_report()
    data["valid"] = False
    if certificate_sha256 is not None:
        data["certificate_sha256"] = certificate_sha256
    if construction_digest is not None:
        data["construction_sha256"] = construction_digest
    if profile is not None:
        data["profile"] = {"id": profile.data["id"], "sha256": profile.sha256}
    data["error"] = error.to_dict()
    return VerificationReport(data)


def _base_report() -> dict[str, Any]:
    return {
        "schema": "euclid-min-verification-report/v1",
        "verifier": {
            "name": VERIFIER_NAME,
            "version": __version__,
            "sage_version": sage_version,
        },
    }
