from __future__ import annotations

from typing import Any, Callable

_todos: dict[str, list[dict[str, Any]]] = {}
_subscribers: list[Callable[[str, list[dict[str, Any]]], None]] = []


def get_todos(session_id: str) -> list[dict[str, Any]]:
    return list(_todos.get(session_id, []))


def set_todos(session_id: str, todos: list[dict[str, Any]]) -> None:
    _todos[session_id] = list(todos)
    for cb in _subscribers:
        cb(session_id, list(todos))


def clear_todos(session_id: str) -> None:
    _todos.pop(session_id, None)
    for cb in _subscribers:
        cb(session_id, [])


def subscribe_todos(callback: Callable[[str, list[dict[str, Any]]], None]) -> Callable[[], None]:
    _subscribers.append(callback)

    def unsubscribe() -> None:
        _subscribers.remove(callback)

    return unsubscribe
