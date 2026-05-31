from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from filelock import FileLock

from ..utils.paths import get_tasks_root

_task_subscribers: list[Callable[[str], None]] = []


def subscribe_tasks(callback: Callable[[str], None]) -> Callable[[], None]:
    _task_subscribers.append(callback)

    def unsubscribe() -> None:
        _task_subscribers.remove(callback)

    return unsubscribe


def _notify_task_change(list_id: str) -> None:
    for cb in _task_subscribers:
        cb(list_id)


def get_task_list_id(session_id: str) -> str:
    return session_id.replace("/", "-").replace("\\", "-")


def _task_list_dir(list_id: str) -> Path:
    return Path(get_tasks_root()) / list_id


def _task_file_path(list_id: str, task_id: str) -> Path:
    return _task_list_dir(list_id) / f"{task_id}.json"


def _lock_path(list_id: str) -> Path:
    return _task_list_dir(list_id) / ".lock"


def _ensure_dir(list_id: str) -> Path:
    d = _task_list_dir(list_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _generate_task_id() -> str:
    return uuid.uuid4().hex[:12]


async def create_task(list_id: str, task_data: dict[str, Any]) -> str:
    _ensure_dir(list_id)
    task_id = task_data.get("id") or _generate_task_id()
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "id": task_id,
        "subject": task_data.get("subject", ""),
        "description": task_data.get("description", ""),
        "active_form": task_data.get("active_form"),
        "owner": task_data.get("owner"),
        "status": task_data.get("status", "pending"),
        "blocks": task_data.get("blocks", []),
        "blocked_by": task_data.get("blocked_by", []),
        "metadata": task_data.get("metadata"),
        "created_at": now,
        "updated_at": now,
    }

    lock = FileLock(str(_lock_path(list_id)))
    with lock:
        _task_file_path(list_id, task_id).write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )

    _notify_task_change(list_id)
    return task_id


async def get_task(list_id: str, task_id: str) -> dict[str, Any] | None:
    path = _task_file_path(list_id, task_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


async def update_task(list_id: str, task_id: str, updates: dict[str, Any]) -> bool:
    path = _task_file_path(list_id, task_id)
    lock = FileLock(str(_lock_path(list_id)))
    with lock:
        if not path.is_file():
            return False
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False

        for key, value in updates.items():
            if key not in ("id", "created_at"):
                record[key] = value
        record["updated_at"] = datetime.now(timezone.utc).isoformat()

        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    _notify_task_change(list_id)
    return True


async def delete_task(list_id: str, task_id: str) -> bool:
    path = _task_file_path(list_id, task_id)
    lock = FileLock(str(_lock_path(list_id)))
    with lock:
        if not path.is_file():
            return False
        path.unlink()
    _notify_task_change(list_id)
    return True


async def list_tasks(list_id: str) -> list[dict[str, Any]]:
    d = _task_list_dir(list_id)
    if not d.is_dir():
        return []

    tasks: list[dict[str, Any]] = []
    lock = FileLock(str(_lock_path(list_id)))
    with lock:
        for f in sorted(d.glob("*.json")):
            if f.name == ".lock":
                continue
            try:
                tasks.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue

    return tasks


async def block_task(list_id: str, blocker_id: str, blocked_id: str) -> bool:
    lock = FileLock(str(_lock_path(list_id)))
    with lock:
        blocker_path = _task_file_path(list_id, blocker_id)
        blocked_path = _task_file_path(list_id, blocked_id)

        if not blocker_path.is_file() or not blocked_path.is_file():
            return False

        try:
            blocker = json.loads(blocker_path.read_text(encoding="utf-8"))
            blocked = json.loads(blocked_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False

        if blocked_id not in blocker.get("blocks", []):
            blocker.setdefault("blocks", []).append(blocked_id)
        if blocker_id not in blocked.get("blocked_by", []):
            blocked.setdefault("blocked_by", []).append(blocker_id)

        now = datetime.now(timezone.utc).isoformat()
        blocker["updated_at"] = now
        blocked["updated_at"] = now

        blocker_path.write_text(json.dumps(blocker, indent=2), encoding="utf-8")
        blocked_path.write_text(json.dumps(blocked, indent=2), encoding="utf-8")

    _notify_task_change(list_id)
    return True
