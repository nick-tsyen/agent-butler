"""
Step 14 - TodoWrite and session-scoped task tracking

Goal:
- let the model keep a visible todo list for complex work
- replace the full list on every write (no ids)
- store todos per session in memory
- auto-clear the list when everything is completed

This file is a teaching version distilled from the real implementation.
"""

from __future__ import annotations

from typing import Any, Callable

# ── Todo schema ────────────────────────────────────────────────────────────────

# Valid values for the status field.
TODO_STATUSES: frozenset[str] = frozenset(["pending", "in_progress", "completed"])


def is_todo_item(value: Any) -> bool:
    """Return True when *value* is a valid TodoItem dict."""
    return (
        isinstance(value, dict)
        and isinstance(value.get("content"), str)
        and value["content"].strip()
        and isinstance(value.get("active_form"), str)
        and value["active_form"].strip()
        and isinstance(value.get("status"), str)
        and value["status"] in TODO_STATUSES
    )


def parse_todos(
    input: dict[str, Any],
) -> list[dict[str, str]] | dict[str, str]:
    """
    Validate and normalise the ``todos`` field from tool input.

    Returns a list of cleaned TodoItem dicts on success, or a dict with
    an ``error`` key describing the validation failure.
    """
    raw = input.get("todos")
    if not isinstance(raw, list):
        return {"error": "`todos` must be an array of TodoItem objects."}

    todos = []
    for idx, item in enumerate(raw):
        if not is_todo_item(item):
            return {
                "error": (
                    f"todos[{idx}] is not a valid TodoItem "
                    "(need non-empty content, active_form, and status in "
                    "pending|in_progress|completed)."
                )
            }
        todos.append({
            "content": item["content"],
            "status": item["status"],
            "active_form": item["active_form"],
        })

    return todos


# ── Session-scoped in-memory store ─────────────────────────────────────────────

# Maps session_id → list of todo items.
_todos_by_session: dict[str, list[dict[str, str]]] = {}

# Set of listener callables; each receives (session_id, todos).
_listeners: set[Callable[[str, list[dict[str, str]]], None]] = set()


def get_todos(session_id: str) -> list[dict[str, str]]:
    """Return the current todo list for *session_id* (empty list if none)."""
    return list(_todos_by_session.get(session_id, []))


def set_todos(session_id: str, todos: list[dict[str, str]]) -> None:
    """Replace the todo list for *session_id* and notify all listeners."""
    _todos_by_session[session_id] = todos
    for listener in _listeners:
        listener(session_id, todos)


def clear_todos(session_id: str) -> None:
    """Clear the todo list for *session_id*."""
    set_todos(session_id, [])


def subscribe_todos(
    listener: Callable[[str, list[dict[str, str]]], None],
) -> Callable[[], None]:
    """
    Register *listener* to be called whenever todos change.

    Returns an unsubscribe callable.
    """
    _listeners.add(listener)

    def unsubscribe() -> None:
        _listeners.discard(listener)

    return unsubscribe


# ── TodoWrite tool ─────────────────────────────────────────────────────────────


class TodoWriteTool:
    """
    Update the todo list for the current session.

    Each call *replaces* the entire list.  When all items are marked
    ``completed``, the list is auto-cleared.
    """

    name = "TodoWrite"
    description = (
        "Update the todo list for the current session. "
        "Use it proactively to track progress and pending tasks."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "The full updated todo list. Each call REPLACES the entire list.",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                        },
                        "active_form": {"type": "string"},
                    },
                    "required": ["content", "status", "active_form"],
                },
            }
        },
        "required": ["todos"],
    }

    def is_read_only(self) -> bool:
        return False  # writes session state

    def is_enabled(self) -> bool:
        return True

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        parsed = parse_todos(input)
        if isinstance(parsed, dict) and "error" in parsed:
            return {"content": f"Error: {parsed['error']}", "is_error": True}

        session_id: str = context.get("session_id") or "default"

        # Auto-clear when every item is completed.
        all_done = len(parsed) > 0 and all(t["status"] == "completed" for t in parsed)
        stored_todos = [] if all_done else parsed  # type: ignore[assignment]

        set_todos(session_id, stored_todos)

        return {
            "content": (
                "Todos have been modified successfully. "
                "Ensure that you continue to use the todo list to track your progress. "
                "Please proceed with the current tasks if applicable"
            )
        }


# ── Permission rule ────────────────────────────────────────────────────────────


def check_permission_for_todo_write(tool_name: str) -> dict[str, str] | None:
    """
    Always allow TodoWrite — it only writes session-scoped in-memory state.

    Returns a permission dict when *tool_name* is ``TodoWrite``, else None.
    """
    if tool_name == "TodoWrite":
        return {"behavior": "allow", "reason": "TodoWrite writes session-only state"}
    return None


# ── Session integration helpers ────────────────────────────────────────────────


def create_tool_context(session_id_ref: Any, cwd: str) -> dict[str, Any]:
    """
    Build a tool context dict with a live session-id getter.

    *session_id_ref* must have a ``.current`` attribute that holds the
    current session ID.  Using a getter ensures resumed sessions always
    read the latest ID without recreating the context object.
    """

    class _Ctx(dict):  # type: ignore[misc]
        @property
        def session_id(self) -> str:  # type: ignore[override]
            return session_id_ref.current

    ctx = _Ctx()
    ctx["cwd"] = cwd
    return ctx


def subscribe_session_todos(
    session_id_ref: Any,
    set_todos_state: Callable[[list[dict[str, str]]], None],
) -> Callable[[], None]:
    """
    Subscribe to todo changes for the current session and sync state.

    Immediately calls *set_todos_state* with the current todos, then
    registers a listener that filters updates to the session in *session_id_ref*.

    Returns an unsubscribe callable.
    """
    set_todos_state(get_todos(session_id_ref.current))

    def _listener(sid: str, next_todos: list[dict[str, str]]) -> None:
        if sid == session_id_ref.current:
            set_todos_state(next_todos)

    return subscribe_todos(_listener)


# ── UI rendering helpers ───────────────────────────────────────────────────────


def count_todos_by_status(todos: list[dict[str, str]], status: str) -> int:
    """Count todos that match *status*."""
    return sum(1 for t in todos if t["status"] == status)


def get_in_progress_todo(todos: list[dict[str, str]]) -> dict[str, str] | None:
    """Return the first in-progress todo, or None."""
    return next((t for t in todos if t["status"] == "in_progress"), None)


def get_effective_spinner_label(todos: list[dict[str, str]], fallback_label: str) -> str:
    """Return the active_form of the in-progress todo, or *fallback_label*."""
    in_progress = get_in_progress_todo(todos)
    return in_progress["active_form"] if in_progress else fallback_label


def format_todo_rows(todos: list[dict[str, str]]) -> list[str]:
    """
    Format each todo as a single display row.

    Rows stay static; only the global status bar spinner animates.
    """
    rows = []
    for todo in todos:
        if todo["status"] == "in_progress":
            rows.append(f"▸ {todo['active_form']}")
        elif todo["status"] == "completed":
            rows.append(f"✓ {todo['content']}")
        else:
            rows.append(f"○ {todo['content']}")
    return rows


# ── Singleton tool instance ────────────────────────────────────────────────────

todo_write_tool = TodoWriteTool()
