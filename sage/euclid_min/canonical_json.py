"""Euclid-Min v1 数据域的 RFC 8785 JSON Canonicalization Scheme。

profile 和证书 Schema 只允许字符串、布尔值、null、安全整数、数组和以
字符串为键的对象。这里有意拒绝 float，从而避开 ECMAScript 浮点序列化，
并保持构造哈希与精确数学边界一致。
"""

from __future__ import annotations

import hashlib
from typing import Any


MAX_SAFE_INTEGER = 9_007_199_254_740_991
MIN_SAFE_INTEGER = -MAX_SAFE_INTEGER


class CanonicalizationError(ValueError):
    """输入不属于 Euclid-Min v1 可规范化数据域。"""


def canonicalize(value: Any) -> bytes:
    """返回 RFC 8785 规范 JSON 的 UTF-8 字节。"""

    return _encode(value).encode("utf-8")


def sha256_hex(value: Any) -> str:
    """返回规范 JSON 数据模型的小写 SHA-256。"""

    return hashlib.sha256(canonicalize(value)).hexdigest()


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if value < MIN_SAFE_INTEGER or value > MAX_SAFE_INTEGER:
            raise CanonicalizationError(
                "JCS 整数必须位于 IEEE-754 安全整数范围内"
            )
        return str(value)
    if isinstance(value, float):
        raise CanonicalizationError("Euclid-Min v1 的规范数据不允许 float")
    if isinstance(value, str):
        return _encode_string(_normalize_surrogates(value))
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        normalized_items: list[tuple[str, Any]] = []
        normalized_keys: set[str] = set()
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("JCS 对象的键必须是字符串")
            normalized_key = _normalize_surrogates(key)
            if normalized_key in normalized_keys:
                raise CanonicalizationError("Unicode 规范化后出现重复对象键")
            normalized_keys.add(normalized_key)
            normalized_items.append((normalized_key, item))
        normalized_items.sort(key=lambda pair: pair[0].encode("utf-16-be"))
        return "{" + ",".join(
            _encode_string(key) + ":" + _encode(item)
            for key, item in normalized_items
        ) + "}"
    raise CanonicalizationError(
        f"Euclid-Min v1 不支持规范化类型 {type(value).__name__}"
    )


def _normalize_surrogates(value: str) -> str:
    """合并合法 UTF-16 代理对，并拒绝孤立代理码点。"""

    try:
        normalized = value.encode("utf-16", "surrogatepass").decode("utf-16")
        normalized.encode("utf-8")
    except UnicodeError as error:
        raise CanonicalizationError("字符串包含非法 Unicode 代理码点") from error
    return normalized


def _encode_string(value: str) -> str:
    escapes = {
        0x08: "\\b",
        0x09: "\\t",
        0x0A: "\\n",
        0x0C: "\\f",
        0x0D: "\\r",
        0x22: '\\"',
        0x5C: "\\\\",
    }
    parts = ['"']
    for character in value:
        codepoint = ord(character)
        if codepoint in escapes:
            parts.append(escapes[codepoint])
        elif codepoint <= 0x1F:
            parts.append(f"\\u{codepoint:04x}")
        else:
            parts.append(character)
    parts.append('"')
    return "".join(parts)
