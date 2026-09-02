"""长时间分片搜索的原子检查点与确定性恢复协议。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from ..canonical_json import sha256_hex
from ..formats import load_profile


SCHEMA_ID = "euclid-min-sharded-search-checkpoint/v1"


class ShardedCheckpointError(ValueError):
    """检查点损坏、任务不匹配或状态转换非法。"""


def _task_definition(
    *,
    task_id: str,
    profile_path: str | Path,
    input_sha256: dict[str, str],
    configuration: dict[str, Any],
    shard_ids: Iterable[str],
) -> dict:
    profile = load_profile(profile_path)
    ordered_shards = list(shard_ids)
    if not task_id:
        raise ValueError("分片任务 ID 不能为空")
    if not ordered_shards or len(set(ordered_shards)) != len(ordered_shards):
        raise ValueError("分片 ID 必须非空且互不重复")
    if any(not shard_id for shard_id in ordered_shards):
        raise ValueError("分片 ID 不能为空")
    if any(
        len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        for digest in input_sha256.values()
    ):
        raise ValueError("输入摘要必须是小写 SHA-256")
    definition = {
        "id": task_id,
        "profile": {"id": profile.data["id"], "sha256": profile.sha256},
        "input_sha256": dict(sorted(input_sha256.items())),
        "configuration": configuration,
        "shard_ids": ordered_shards,
    }
    definition["signature"] = sha256_hex(definition)
    return definition


def _fresh_payload(task: dict) -> dict:
    return {
        "schema": SCHEMA_ID,
        "task": task,
        "progress": {
            "status": "running",
            "revision": 0,
            "completed_shards": [],
        },
    }


def _validate_payload(payload: dict) -> None:
    if payload.get("schema") != SCHEMA_ID:
        raise ShardedCheckpointError("检查点 schema 不受支持")
    try:
        task = payload["task"]
        progress = payload["progress"]
        shard_ids = task["shard_ids"]
        completed = progress["completed_shards"]
    except (KeyError, TypeError) as error:
        raise ShardedCheckpointError("检查点缺少必要字段") from error
    if len(task.get("signature", "")) != 64:
        raise ShardedCheckpointError("检查点任务签名无效")
    unsigned = {key: value for key, value in task.items() if key != "signature"}
    if sha256_hex(unsigned) != task["signature"]:
        raise ShardedCheckpointError("检查点任务定义与签名不一致")
    if len(shard_ids) != len(set(shard_ids)):
        raise ShardedCheckpointError("检查点包含重复分片 ID")
    completed_ids = [item.get("id") for item in completed]
    if len(completed_ids) != len(set(completed_ids)):
        raise ShardedCheckpointError("检查点包含重复的已完成分片")
    if any(shard_id not in shard_ids for shard_id in completed_ids):
        raise ShardedCheckpointError("检查点包含任务定义之外的分片")
    expected_order = [
        shard_id for shard_id in shard_ids if shard_id in set(completed_ids)
    ]
    if completed_ids != expected_order:
        raise ShardedCheckpointError("已完成分片没有按任务顺序保存")
    if progress.get("status") not in {"running", "paused", "completed"}:
        raise ShardedCheckpointError("检查点状态无效")
    if not isinstance(progress.get("revision"), int) or progress["revision"] < 0:
        raise ShardedCheckpointError("检查点 revision 无效")
    if progress["status"] == "completed" and len(completed) != len(shard_ids):
        raise ShardedCheckpointError("任务未完成全部分片却标记为 completed")


def _read(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ShardedCheckpointError(f"无法读取检查点: {error}") from error
    if not isinstance(payload, dict):
        raise ShardedCheckpointError("检查点根节点必须是 JSON 对象")
    _validate_payload(payload)
    return payload


def _atomic_write(path: Path, payload: dict) -> None:
    """同目录写入、fsync 后原子替换，崩溃至多丢失当前分片。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
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


def load_or_create_checkpoint(
    path: str | Path,
    *,
    task_id: str,
    profile_path: str | Path,
    input_sha256: dict[str, str],
    configuration: dict[str, Any],
    shard_ids: Iterable[str],
) -> dict:
    """加载同一任务的检查点，或原子创建一个新检查点。"""

    checkpoint_path = Path(path)
    expected_task = _task_definition(
        task_id=task_id,
        profile_path=profile_path,
        input_sha256=input_sha256,
        configuration=configuration,
        shard_ids=shard_ids,
    )
    if checkpoint_path.exists():
        payload = _read(checkpoint_path)
        if payload["task"] != expected_task:
            raise ShardedCheckpointError(
                "检查点与当前任务、profile、输入摘要、配置或分片安排不一致"
            )
        return payload
    payload = _fresh_payload(expected_task)
    _atomic_write(checkpoint_path, payload)
    return payload


def remaining_shard_ids(payload: dict) -> tuple[str, ...]:
    _validate_payload(payload)
    completed = {
        item["id"] for item in payload["progress"]["completed_shards"]
    }
    return tuple(
        shard_id
        for shard_id in payload["task"]["shard_ids"]
        if shard_id not in completed
    )


def record_completed_shard(
    path: str | Path,
    payload: dict,
    *,
    shard_id: str,
    result: dict[str, Any],
) -> dict:
    """记录一个完整分片；当前分片中途崩溃时不会被错误标为完成。"""

    _validate_payload(payload)
    if shard_id not in payload["task"]["shard_ids"]:
        raise ShardedCheckpointError(f"未知分片 {shard_id!r}")
    completed_by_id = {
        item["id"]: item for item in payload["progress"]["completed_shards"]
    }
    if shard_id in completed_by_id:
        if completed_by_id[shard_id]["result"] != result:
            raise ShardedCheckpointError(
                f"分片 {shard_id!r} 已完成且结果不一致"
            )
        return payload
    completed_by_id[shard_id] = {"id": shard_id, "result": result}
    ordered_completed = [
        completed_by_id[item]
        for item in payload["task"]["shard_ids"]
        if item in completed_by_id
    ]
    updated = {
        **payload,
        "progress": {
            "status": "running",
            "revision": payload["progress"]["revision"] + 1,
            "completed_shards": ordered_completed,
        },
    }
    _atomic_write(Path(path), updated)
    return updated


def set_checkpoint_status(
    path: str | Path,
    payload: dict,
    status: str,
) -> dict:
    """把任务标记为 running、paused 或 completed。"""

    _validate_payload(payload)
    if status not in {"running", "paused", "completed"}:
        raise ValueError(f"不支持的检查点状态 {status!r}")
    if status == "completed" and remaining_shard_ids(payload):
        raise ShardedCheckpointError("仍有未完成分片，不能标记为 completed")
    if payload["progress"]["status"] == status:
        return payload
    updated = {
        **payload,
        "progress": {
            **payload["progress"],
            "status": status,
            "revision": payload["progress"]["revision"] + 1,
        },
    }
    _atomic_write(Path(path), updated)
    return updated


def load_checkpoint(path: str | Path) -> dict:
    """只读加载并验证检查点，供报告和测试使用。"""

    return _read(Path(path))
