"""profile、证书和 JSON Schema 的严格加载。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .canonical_json import CanonicalizationError, sha256_hex
from .errors import VerificationError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE_SCHEMA = REPOSITORY_ROOT / "schemas" / "profile-v1.schema.json"
DEFAULT_CERTIFICATE_SCHEMA = (
    REPOSITORY_ROOT / "schemas" / "certificate-v1.schema.json"
)


class DuplicateKeyError(ValueError):
    """JSON 或 YAML 对象包含重复键。"""


class UniqueKeySafeLoader(yaml.SafeLoader):
    """禁用自定义 tag 并拒绝重复 mapping key 的 YAML loader。"""


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as error:
            raise DuplicateKeyError("YAML mapping key 必须可哈希") from error
        if duplicate:
            raise DuplicateKeyError(f"重复的 YAML mapping key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True, slots=True)
class LoadedProfile:
    path: Path
    data: dict[str, Any]
    sha256: str


@dataclass(frozen=True, slots=True)
class LoadedCertificate:
    path: Path
    data: dict[str, Any]
    file_sha256: str


def load_profile(
    path: str | Path,
    schema_path: str | Path = DEFAULT_PROFILE_SCHEMA,
) -> LoadedProfile:
    profile_path = Path(path)
    try:
        text = profile_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise VerificationError(
            "profile_read_error",
            f"无法读取 UTF-8 profile: {profile_path}",
        ) from error

    try:
        data = yaml.load(text, Loader=UniqueKeySafeLoader)
    except (yaml.YAMLError, DuplicateKeyError) as error:
        raise VerificationError("profile_yaml_invalid", str(error)) from error

    schema = _load_schema(schema_path)
    _validate_schema_instance(data, schema, "profile_schema_invalid")
    try:
        digest = sha256_hex(data)
    except CanonicalizationError as error:
        raise VerificationError("profile_canonicalization_failed", str(error)) from error
    return LoadedProfile(profile_path, data, digest)


def load_certificate(
    path: str | Path,
    schema_path: str | Path = DEFAULT_CERTIFICATE_SCHEMA,
) -> LoadedCertificate:
    certificate_path = Path(path)
    try:
        raw = certificate_path.read_bytes()
    except OSError as error:
        raise VerificationError(
            "certificate_read_error",
            f"无法读取证书: {certificate_path}",
        ) from error

    file_digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise VerificationError(
            "certificate_json_invalid",
            "证书不是有效 UTF-8 文本",
            details={"certificate_sha256": file_digest},
        ) from error

    try:
        data = json.loads(text, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, DuplicateKeyError) as error:
        raise VerificationError(
            "certificate_json_invalid",
            str(error),
            details={"certificate_sha256": file_digest},
        ) from error

    schema = _load_schema(schema_path)
    try:
        _validate_schema_instance(data, schema, "schema_invalid")
    except VerificationError as error:
        error.details.setdefault("certificate_sha256", file_digest)
        raise
    return LoadedCertificate(certificate_path, data, file_digest)


def construction_sha256(construction: dict[str, Any]) -> str:
    try:
        return sha256_hex(construction)
    except CanonicalizationError as error:
        raise VerificationError(
            "construction_canonicalization_failed", str(error)
        ) from error


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"重复的 JSON object key: {key!r}")
        result[key] = value
    return result


def _load_schema(path: str | Path) -> dict[str, Any]:
    schema_path = Path(path)
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(
            "schema_load_error", f"无法加载 JSON Schema: {schema_path}"
        ) from error


def _validate_schema_instance(
    instance: Any,
    schema: dict[str, Any],
    error_code: str,
) -> None:
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(instance),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
    except Exception as error:
        raise VerificationError(
            "schema_load_error", "JSON Schema 本身无效"
        ) from error

    if not errors:
        return
    first = errors[0]
    instance_path = "/".join(str(part) for part in first.absolute_path)
    raise VerificationError(
        error_code,
        first.message,
        details={"instance_path": instance_path},
    )
