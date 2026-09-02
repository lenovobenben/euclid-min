"""候选级追加日志：每条结果 fsync，断电后可从最后完整记录恢复。"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ..canonical_json import sha256_hex


SCHEMA_ID = "euclid-min-durable-search-journal/v1"


class DurableJournalError(ValueError):
    """日志损坏、哈希链断裂或任务定义不匹配。"""


@dataclass(slots=True)
class JournalSnapshot:
    task: dict[str, Any]
    events: list[dict[str, Any]]
    valid_bytes: int
    last_hash: str


def _event_hash(unsigned_event: dict[str, Any]) -> str:
    # 运行事件含耗时等有限浮点数，不能使用证书层故意禁止 float 的 v1
    # canonical JSON；sort_keys + 紧凑编码足以为本地日志提供确定性哈希链。
    encoded = json.dumps(
        unsigned_event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _signed_event(
    *,
    sequence: int,
    previous_sha256: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    unsigned = {
        "sequence": sequence,
        "previous_sha256": previous_sha256,
        "type": event_type,
        "payload": payload,
    }
    return {**unsigned, "sha256": _event_hash(unsigned)}


def task_definition(
    *,
    task_id: str,
    input_sha256: dict[str, str],
    configuration: dict[str, Any],
    work_ids: Iterable[str],
) -> dict[str, Any]:
    """构造带签名的不可变任务定义。"""

    ordered_work_ids = list(work_ids)
    if not task_id:
        raise ValueError("任务 ID 不能为空")
    if not ordered_work_ids or len(set(ordered_work_ids)) != len(ordered_work_ids):
        raise ValueError("工作单元 ID 必须非空且互不重复")
    if any(not work_id for work_id in ordered_work_ids):
        raise ValueError("工作单元 ID 不能为空")
    if any(
        len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        for digest in input_sha256.values()
    ):
        raise ValueError("输入摘要必须是小写 SHA-256")
    definition = {
        "id": task_id,
        "input_sha256": dict(sorted(input_sha256.items())),
        "configuration": configuration,
        "work_ids": ordered_work_ids,
    }
    definition["signature"] = sha256_hex(definition)
    return definition


def _encode_line(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _atomic_create(path: Path, header: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(_encode_line(header))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def _validate_task(task: dict[str, Any]) -> None:
    signature = task.get("signature")
    if not isinstance(signature, str) or len(signature) != 64:
        raise DurableJournalError("日志任务签名无效")
    unsigned = {key: value for key, value in task.items() if key != "signature"}
    if sha256_hex(unsigned) != signature:
        raise DurableJournalError("日志任务定义与签名不一致")
    work_ids = task.get("work_ids")
    if not isinstance(work_ids, list) or not work_ids:
        raise DurableJournalError("日志没有工作单元")
    if len(work_ids) != len(set(work_ids)):
        raise DurableJournalError("日志含重复工作单元 ID")


def load_journal(path: str | Path) -> JournalSnapshot:
    """读取并校验完整行；只容忍 EOF 处尚未落完的一条记录。"""

    journal_path = Path(path)
    try:
        raw = journal_path.read_bytes()
    except OSError as error:
        raise DurableJournalError(f"无法读取日志: {error}") from error
    lines = raw.splitlines(keepends=True)
    if not lines or not lines[0].endswith(b"\n"):
        raise DurableJournalError("日志头不完整")
    try:
        header = json.loads(lines[0].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise DurableJournalError("日志头不是有效 JSON") from error
    if header.get("schema") != SCHEMA_ID or header.get("type") != "header":
        raise DurableJournalError("日志头 schema 不受支持")
    task = header.get("task")
    if not isinstance(task, dict):
        raise DurableJournalError("日志头缺少任务定义")
    _validate_task(task)

    valid_bytes = len(lines[0])
    previous_hash = task["signature"]
    events: list[dict[str, Any]] = []
    for line_index, line in enumerate(lines[1:], start=1):
        if not line.endswith(b"\n"):
            if line_index != len(lines) - 1:
                raise DurableJournalError("日志中部出现不完整记录")
            break
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise DurableJournalError(
                f"第 {line_index + 1} 行不是有效 JSON"
            ) from error
        if not isinstance(event, dict):
            raise DurableJournalError(f"第 {line_index + 1} 行必须是对象")
        expected_sequence = len(events)
        if event.get("sequence") != expected_sequence:
            raise DurableJournalError("日志事件序号不连续")
        if event.get("previous_sha256") != previous_hash:
            raise DurableJournalError("日志哈希链断裂")
        event_hash = event.get("sha256")
        unsigned = {key: value for key, value in event.items() if key != "sha256"}
        if event_hash != _event_hash(unsigned):
            raise DurableJournalError("日志事件摘要不一致")
        if not isinstance(event.get("type"), str) or not isinstance(
            event.get("payload"), dict
        ):
            raise DurableJournalError("日志事件字段无效")
        events.append(event)
        previous_hash = event_hash
        valid_bytes += len(line)
    return JournalSnapshot(task, events, valid_bytes, previous_hash)


def load_or_create_journal(
    path: str | Path,
    *,
    task: dict[str, Any],
) -> JournalSnapshot:
    """创建日志或恢复同一任务；自动舍弃崩溃留下的 EOF 碎片。"""

    journal_path = Path(path)
    _validate_task(task)
    if not journal_path.exists():
        _atomic_create(
            journal_path,
            {"schema": SCHEMA_ID, "type": "header", "task": task},
        )
    snapshot = load_journal(journal_path)
    if snapshot.task != task:
        raise DurableJournalError("日志与当前输入、配置或工作单元不匹配")
    file_size = journal_path.stat().st_size
    if snapshot.valid_bytes != file_size:
        with journal_path.open("r+b") as stream:
            stream.truncate(snapshot.valid_bytes)
            stream.flush()
            os.fsync(stream.fileno())
    return snapshot


def append_event(
    path: str | Path,
    snapshot: JournalSnapshot,
    *,
    event_type: str,
    payload: dict[str, Any],
) -> JournalSnapshot:
    """追加并 fsync 一条事件，返回包含该事件的新快照。"""

    if not event_type:
        raise ValueError("事件类型不能为空")
    journal_path = Path(path)
    if journal_path.stat().st_size != snapshot.valid_bytes:
        raise DurableJournalError("日志已被其他写入者改变")
    event = _signed_event(
        sequence=len(snapshot.events),
        previous_sha256=snapshot.last_hash,
        event_type=event_type,
        payload=payload,
    )
    encoded = _encode_line(event)
    with journal_path.open("ab") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    snapshot.events.append(event)
    snapshot.valid_bytes += len(encoded)
    snapshot.last_hash = event["sha256"]
    return snapshot


def file_sha256(path: str | Path) -> str:
    """返回文件的小写 SHA-256。"""

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
