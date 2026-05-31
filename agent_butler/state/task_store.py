from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from filelock import FileLock

from ..utils.paths import get_tasks_root, get_harness_root
import os

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


def _get_harness_feature_list_path() -> Path | None:
    harness_root = get_harness_root(os.getcwd())
    if harness_root:
        p = Path(harness_root) / "feature_list.json"
        if p.is_file():
            return p
    return None


def _map_feature_to_task(f: dict[str, Any]) -> dict[str, Any]:
    status_map = {
        "not_started": "pending",
        "in_progress": "in_progress",
        "passing": "completed",
        "blocked": "blocked"
    }
    return {
        "id": f.get("id"),
        "subject": f.get("title", ""),
        "description": f.get("behavior", ""),
        "status": status_map.get(f.get("status"), "pending"),
        "blocks": f.get("blocks", []),
        "blocked_by": f.get("blocked_by", []),
        "metadata": {
            "priority": f.get("priority"),
            "area": f.get("area"),
            "verification_command": f.get("verification_command"),
            "verification": f.get("verification"),
            "evidence": f.get("evidence"),
            "notes": f.get("notes")
        }
    }


def _map_task_to_feature(task_data: dict[str, Any]) -> dict[str, Any]:
    status_map = {
        "pending": "not_started",
        "in_progress": "in_progress",
        "completed": "passing",
        "blocked": "blocked"
    }
    meta = task_data.get("metadata") or {}
    f = {
        "id": task_data.get("id"),
        "title": task_data.get("subject", ""),
        "behavior": task_data.get("description", ""),
        "status": status_map.get(task_data.get("status", "pending"), "not_started"),
        "blocks": task_data.get("blocks", []),
        "blocked_by": task_data.get("blocked_by", []),
    }
    if isinstance(meta, dict):
        for k in ("priority", "area", "verification_command", "verification", "notes"):
            if k in meta:
                f[k] = meta[k]
        if "evidence" in meta:
            if isinstance(meta["evidence"], list):
                f["evidence"] = list(meta["evidence"])
            else:
                f["evidence"] = [str(meta["evidence"])]
    return f


async def create_task(list_id: str, task_data: dict[str, Any]) -> str:
    fl_path = _get_harness_feature_list_path()
    if fl_path:
        lock = FileLock(str(fl_path.with_name(".feature_list.lock")))
        with lock:
            try:
                data = json.loads(fl_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {"features": []}
            
            features = data.setdefault("features", [])
            task_id = task_data.get("id") or _generate_task_id()
            
            status_map = {
                "pending": "not_started",
                "in_progress": "in_progress",
                "completed": "passing",
                "blocked": "blocked"
            }
            new_status = status_map.get(task_data.get("status", "pending"), "not_started")
            if new_status == "in_progress":
                for f in features:
                    if f.get("status") == "in_progress":
                        raise ValueError("WIP=1 constraint is active. You cannot start a new feature until the active feature is passing or blocked.")
            
            task_copy = dict(task_data)
            task_copy["id"] = task_id
            new_feature = _map_task_to_feature(task_copy)
            features.append(new_feature)
            
            fl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _notify_task_change(list_id)
        return task_id

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
    fl_path = _get_harness_feature_list_path()
    if fl_path:
        lock = FileLock(str(fl_path.with_name(".feature_list.lock")))
        with lock:
            try:
                data = json.loads(fl_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
            features = data.get("features", [])
            for f in features:
                if f.get("id") == task_id:
                    return _map_feature_to_task(f)
            return None

    path = _task_file_path(list_id, task_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


async def update_task(list_id: str, task_id: str, updates: dict[str, Any]) -> bool:
    fl_path = _get_harness_feature_list_path()
    if fl_path:
        lock = FileLock(str(fl_path.with_name(".feature_list.lock")))
        with lock:
            try:
                data = json.loads(fl_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return False
            features = data.get("features", [])
            target = None
            for f in features:
                if f.get("id") == task_id:
                    target = f
                    break
            if not target:
                return False
                
            new_status_raw = updates.get("status")
            if new_status_raw:
                status_map = {
                    "pending": "not_started",
                    "in_progress": "in_progress",
                    "completed": "passing",
                    "blocked": "blocked"
                }
                new_status = status_map.get(new_status_raw)
                
                if new_status == "in_progress":
                    for f in features:
                        if f.get("id") != task_id and f.get("status") == "in_progress":
                            raise ValueError("WIP=1 constraint is active. You cannot start a new feature until the active feature is passing or blocked.")
                            
                target["status"] = new_status
                
            if "subject" in updates:
                target["title"] = updates["subject"]
            if "description" in updates:
                target["behavior"] = updates["description"]
            
            meta = updates.get("metadata")
            if isinstance(meta, dict):
                for k in ("priority", "area", "verification_command", "verification", "notes"):
                    if k in meta:
                        target[k] = meta[k]
                if "evidence" in meta:
                    ev = target.setdefault("evidence", [])
                    if isinstance(meta["evidence"], list):
                        ev.extend(meta["evidence"])
                    else:
                        ev.append(str(meta["evidence"]))
                        
            if "blocks" in updates:
                target["blocks"] = updates["blocks"]
            if "blocked_by" in updates:
                target["blocked_by"] = updates["blocked_by"]
                
            fl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _notify_task_change(list_id)
        return True

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
    fl_path = _get_harness_feature_list_path()
    if fl_path:
        lock = FileLock(str(fl_path.with_name(".feature_list.lock")))
        with lock:
            try:
                data = json.loads(fl_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return False
            features = data.get("features", [])
            initial_len = len(features)
            features = [f for f in features if f.get("id") != task_id]
            if len(features) == initial_len:
                return False
            data["features"] = features
            fl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _notify_task_change(list_id)
        return True

    path = _task_file_path(list_id, task_id)
    lock = FileLock(str(_lock_path(list_id)))
    with lock:
        if not path.is_file():
            return False
        path.unlink()
    _notify_task_change(list_id)
    return True


async def list_tasks(list_id: str) -> list[dict[str, Any]]:
    fl_path = _get_harness_feature_list_path()
    if fl_path:
        lock = FileLock(str(fl_path.with_name(".feature_list.lock")))
        with lock:
            try:
                data = json.loads(fl_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
            features = data.get("features", [])
            return [_map_feature_to_task(f) for f in features]

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
    fl_path = _get_harness_feature_list_path()
    if fl_path:
        lock = FileLock(str(fl_path.with_name(".feature_list.lock")))
        with lock:
            try:
                data = json.loads(fl_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return False
            features = data.get("features", [])
            blocker = None
            blocked = None
            for f in features:
                if f.get("id") == blocker_id:
                    blocker = f
                if f.get("id") == blocked_id:
                    blocked = f
            if not blocker or not blocked:
                return False
            
            if blocked_id not in blocker.get("blocks", []):
                blocker.setdefault("blocks", []).append(blocked_id)
            if blocker_id not in blocked.get("blocked_by", []):
                blocked.setdefault("blocked_by", []).append(blocker_id)
                
            fl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _notify_task_change(list_id)
        return True

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
