from __future__ import annotations

from typing import Callable

_task_mode_enabled = True
_todo_mode_enabled = False
_subscribers: list[Callable[[str], None]] = []


def is_task_mode_enabled() -> bool:
    return _task_mode_enabled


def is_todo_mode_enabled() -> bool:
    return _todo_mode_enabled


def get_task_mode() -> str:
    if _task_mode_enabled:
        return "task"
    if _todo_mode_enabled:
        return "todo"
    return "off"


def set_task_mode(mode: str) -> None:
    global _task_mode_enabled, _todo_mode_enabled
    mode_lower = mode.strip().lower()
    if mode_lower == "task":
        _task_mode_enabled = True
        _todo_mode_enabled = False
    elif mode_lower == "todo":
        _task_mode_enabled = False
        _todo_mode_enabled = True
    elif mode_lower == "off":
        _task_mode_enabled = False
        _todo_mode_enabled = False
    elif mode_lower == "on":
        _task_mode_enabled = True
    for cb in _subscribers:
        cb(get_task_mode())


def subscribe_task_mode(callback: Callable[[str], None]) -> Callable[[], None]:
    _subscribers.append(callback)

    def unsubscribe() -> None:
        _subscribers.remove(callback)

    return unsubscribe
