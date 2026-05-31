from __future__ import annotations

from typing import Any

from .storage import load_session, save_session


async def append_message(session_id: str, message: dict[str, Any]) -> None:
    history = await load_session(session_id) or []
    history.append(message)
    await save_session(session_id, history)


async def get_history(session_id: str) -> list[dict[str, Any]]:
    return await load_session(session_id) or []
