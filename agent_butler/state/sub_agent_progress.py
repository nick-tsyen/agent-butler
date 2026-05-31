from __future__ import annotations

from typing import Any, Callable

_progress: dict[str, dict[str, Any]] = {}
_subscribers: list[Callable[[str, dict[str, Any] | None], None]] = []


def _notify(key: str, snapshot: dict[str, Any] | None) -> None:
    for cb in _subscribers:
        cb(key, snapshot)


def subscribe_sub_agent_progress(
    callback: Callable[[str, dict[str, Any] | None], None],
) -> Callable[[], None]:
    _subscribers.append(callback)

    def unsubscribe() -> None:
        _subscribers.remove(callback)

    return unsubscribe


def start_sub_agent_progress(key: str, info: dict[str, Any]) -> None:
    _progress[key] = {
        "status": "running",
        "started_at": info.get("started_at"),
        "description": info.get("description", ""),
        "agent_type": info.get("agent_type", ""),
        "updates": [],
        "result": None,
    }
    _notify(key, dict(_progress[key]))


def update_sub_agent_progress(key: str, updates: dict[str, Any]) -> None:
    entry = _progress.get(key)
    if not entry:
        return
    entry["updates"].append(updates)
    if "description" in updates:
        entry["description"] = updates["description"]
    if "status" in updates:
        entry["status"] = updates["status"]
    _notify(key, dict(entry))


def complete_sub_agent_progress(key: str, result: dict[str, Any]) -> None:
    entry = _progress.get(key)
    if not entry:
        return
    entry["status"] = "completed"
    entry["result"] = result
    _notify(key, dict(entry))


def get_sub_agent_progress(key: str) -> dict[str, Any] | None:
    entry = _progress.get(key)
    if entry is None:
        return None
    return dict(entry)


def get_all_progress() -> dict[str, dict[str, Any]]:
    return {k: dict(v) for k, v in _progress.items()}


def clear_progress(key: str) -> bool:
    existed = _progress.pop(key, None) is not None
    if existed:
        _notify(key, None)
    return existed
