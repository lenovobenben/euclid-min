"""验证器对外稳定的错误对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VerificationError(Exception):
    """预期内的证书、profile 或程序验证失败。"""

    code: str
    message: str
    program_index: int | None = None
    entry_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.program_index is not None:
            result["program_index"] = self.program_index
        if self.entry_id is not None:
            result["entry_id"] = self.entry_id
        if self.details:
            result["details"] = self.details
        return result
