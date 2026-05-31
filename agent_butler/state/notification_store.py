from __future__ import annotations

from typing import Any, Callable

_notifications: list[dict[str, Any]] = []
_subscribers: list[Callable[[], None]] = []


def add_notification(notification: dict[str, Any]) -> None:
    _notifications.append(notification)
    for cb in _subscribers:
        cb()


def get_pending_notifications() -> list[dict[str, Any]]:
    return list(_notifications)


def pending_notification_count() -> int:
    return len(_notifications)


def pop_all_notifications() -> list[dict[str, Any]]:
    items = list(_notifications)
    _notifications.clear()
    return items


def clear_notifications() -> None:
    _notifications.clear()


def subscribe_pending_notifications(callback: Callable[[], None]) -> Callable[[], None]:
    _subscribers.append(callback)

    def unsubscribe() -> None:
        _subscribers.remove(callback)

    return unsubscribe
