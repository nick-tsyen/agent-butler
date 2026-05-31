"""
Step 15 - Persistent task graph (Task V2)

Goal:
- replace the in-memory todo note with persistent task files
- keep stable numeric ids across restarts
- support dependency edges with blocks / blocked_by
- expose a small task toolset for create / list / get / update
- keep the UI synced through an in-process refresh signal

This file is a teaching version that condenses the core mechanics.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import aiofiles

# ── Constants ─────────────────────────────────────────────────────────────────

AGENT_BUTLER_HOME: Path = Path.home() / ".agent-butler"
TASKS_ROOT: Path = AGENT_BUTLER_HOME / "tasks"
HIGH_WATER_MARK_FILE: str = ".highwatermark"

TASK_STATUSES: list[str] = ["pending", "in_progress", "completed"]


# ── Task model ─────────────────────────────────────────────────────────────────


def create_task_record(id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build a normalised task dict from raw *data*."""
    return {
        "id": id,
        "subject": data.get("subject", ""),
        "description": data.get("description", ""),
        "active_form": data.get("active_form"),
        "owner": data.get("owner"),
        "status": data.get("status") or "pending",
        "blocks": data.get("blocks") or [],
        "blocked_by": data.get("blocked_by") or [],
        "metadata": data.get("metadata"),
    }


# ── Path layout ───────────────────────────────────────────────────────────────


def sanitize_path_component(value: Any) -> str:
    """Replace non-alphanumeric characters with dashes for safe filenames."""
    return re.sub(r"[^A-Za-z0-9_-]", "-", str(value))


def get_task_list_id(session_id: str | None) -> str:
    """Return the task list ID for *session_id*, defaulting to 'default'."""
    return session_id or "default"


def get_tasks_dir(task_list_id: str) -> Path:
    """Return the directory that stores all tasks for *task_list_id*."""
    return TASKS_ROOT / sanitize_path_component(task_list_id)


def get_task_path(task_list_id: str, task_id: str) -> Path:
    """Return the JSON file path for a specific task."""
    return get_tasks_dir(task_list_id) / f"{sanitize_path_component(task_id)}.json"


def _get_high_water_mark_path(task_list_id: str) -> Path:
    return get_tasks_dir(task_list_id) / HIGH_WATER_MARK_FILE


async def _ensure_tasks_dir(task_list_id: str) -> None:
    get_tasks_dir(task_list_id).mkdir(parents=True, exist_ok=True)


# ── High water mark (stable IDs) ──────────────────────────────────────────────


async def _read_high_water_mark(task_list_id: str) -> int:
    """Read the high water mark for *task_list_id*, defaulting to 0."""
    try:
        async with aiofiles.open(_get_high_water_mark_path(task_list_id), encoding="utf-8") as f:
            value = (await f.read()).strip()
        n = int(value) if value else 0
        return max(n, 0)
    except (FileNotFoundError, ValueError):
        return 0


async def _write_high_water_mark(task_list_id: str, value: int) -> None:
    await _ensure_tasks_dir(task_list_id)
    async with aiofiles.open(_get_high_water_mark_path(task_list_id), "w", encoding="utf-8") as f:
        await f.write(str(value))


async def _find_highest_task_id_from_files(task_list_id: str) -> int:
    """Scan all JSON task files and return the highest numeric ID found."""
    tasks_dir = get_tasks_dir(task_list_id)
    try:
        files = list(tasks_dir.iterdir())
    except FileNotFoundError:
        return 0

    highest = 0
    for file in files:
        if file.suffix != ".json":
            continue
        try:
            n = int(file.stem)
            if n > highest:
                highest = n
        except ValueError:
            pass
    return highest


async def _find_highest_task_id(task_list_id: str) -> int:
    from_files, from_mark = await asyncio.gather(
        _find_highest_task_id_from_files(task_list_id),
        _read_high_water_mark(task_list_id),
    )
    return max(from_files, from_mark)


# ── Read / write helpers ──────────────────────────────────────────────────────


def _parse_task(raw: Any) -> dict[str, Any] | None:
    """Validate and normalise a raw task dict. Returns None if invalid."""
    if not isinstance(raw, dict):
        return None
    if not isinstance(raw.get("id"), str):
        return None
    if not isinstance(raw.get("subject"), str):
        return None
    if not isinstance(raw.get("description"), str):
        return None
    if raw.get("status") not in TASK_STATUSES:
        return None

    return {
        "id": raw["id"],
        "subject": raw["subject"],
        "description": raw["description"],
        "active_form": raw.get("active_form") if isinstance(raw.get("active_form"), str) else None,
        "owner": raw.get("owner") if isinstance(raw.get("owner"), str) else None,
        "status": raw["status"],
        "blocks": [i for i in raw.get("blocks", []) if isinstance(i, str)],
        "blocked_by": [i for i in raw.get("blocked_by", []) if isinstance(i, str)],
        "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else None,
    }


async def get_task(task_list_id: str, task_id: str) -> dict[str, Any] | None:
    """Read and parse a task from disk. Returns None if missing or invalid."""
    try:
        async with aiofiles.open(get_task_path(task_list_id, task_id), encoding="utf-8") as f:
            content = await f.read()
        return _parse_task(json.loads(content))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


async def list_tasks(task_list_id: str) -> list[dict[str, Any]]:
    """Return all valid tasks in *task_list_id*, in any order."""
    tasks_dir = get_tasks_dir(task_list_id)
    try:
        files = list(tasks_dir.iterdir())
    except FileNotFoundError:
        return []

    ids = [f.stem for f in files if f.suffix == ".json" and not f.name.startswith(".")]
    tasks = await asyncio.gather(*[get_task(task_list_id, id) for id in ids])
    return [t for t in tasks if t is not None]


async def _write_task(task_list_id: str, task: dict[str, Any]) -> None:
    await _ensure_tasks_dir(task_list_id)
    async with aiofiles.open(get_task_path(task_list_id, task["id"]), "w", encoding="utf-8") as f:
        await f.write(json.dumps(task, indent=2))


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def create_task(task_list_id: str, data: dict[str, Any]) -> str:
    """Create a new task and return its stable numeric ID string."""
    next_id = str(await _find_highest_task_id(task_list_id) + 1)
    task = create_task_record(next_id, {**data, "status": data.get("status") or "pending"})
    await _write_task(task_list_id, task)
    return next_id


async def update_task(
    task_list_id: str, task_id: str, updates: dict[str, Any]
) -> dict[str, Any] | None:
    """Apply *updates* to an existing task and persist it. Returns None if not found."""
    existing = await get_task(task_list_id, task_id)
    if existing is None:
        return None
    updated = {**existing, **updates, "id": task_id}
    await _write_task(task_list_id, updated)
    return updated


async def delete_task(task_list_id: str, task_id: str) -> bool:
    """
    Delete a task file.

    Updates the high water mark to preserve ID monotonicity, then
    removes references to *task_id* from sibling tasks.
    """
    try:
        numeric_id = int(task_id)
        mark = await _read_high_water_mark(task_list_id)
        if numeric_id > mark:
            await _write_high_water_mark(task_list_id, numeric_id)
    except ValueError:
        pass

    task_path = get_task_path(task_list_id, task_id)
    try:
        task_path.unlink()
    except FileNotFoundError:
        return False

    # Cascade: remove references from sibling tasks.
    siblings = await list_tasks(task_list_id)
    for sibling in siblings:
        next_blocks = [b for b in sibling["blocks"] if b != task_id]
        next_blocked_by = [b for b in sibling["blocked_by"] if b != task_id]
        if len(next_blocks) != len(sibling["blocks"]) or len(next_blocked_by) != len(sibling["blocked_by"]):
            await update_task(task_list_id, sibling["id"], {
                "blocks": next_blocks,
                "blocked_by": next_blocked_by,
            })

    return True


async def reset_task_list(task_list_id: str) -> None:
    """Delete all task JSON files while preserving the high water mark."""
    current_highest = await _find_highest_task_id_from_files(task_list_id)
    if current_highest > 0:
        existing_mark = await _read_high_water_mark(task_list_id)
        if current_highest > existing_mark:
            await _write_high_water_mark(task_list_id, current_highest)

    tasks_dir = get_tasks_dir(task_list_id)
    try:
        files = list(tasks_dir.iterdir())
    except FileNotFoundError:
        return

    for file in files:
        if file.suffix == ".json" and not file.name.startswith("."):
            try:
                file.unlink()
            except FileNotFoundError:
                pass


# ── Dependency graph helpers ───────────────────────────────────────────────────


async def block_task(
    task_list_id: str, from_task_id: str, to_task_id: str
) -> bool:
    """
    Add a dependency edge: *from_task_id* blocks *to_task_id*.

    Updates both tasks' ``blocks`` and ``blocked_by`` lists.
    Returns False if either task does not exist.
    """
    from_task, to_task = await asyncio.gather(
        get_task(task_list_id, from_task_id),
        get_task(task_list_id, to_task_id),
    )
    if from_task is None or to_task is None:
        return False

    if to_task_id not in from_task["blocks"]:
        await update_task(task_list_id, from_task_id, {
            "blocks": [*from_task["blocks"], to_task_id]
        })

    if from_task_id not in to_task["blocked_by"]:
        await update_task(task_list_id, to_task_id, {
            "blocked_by": [*to_task["blocked_by"], from_task_id]
        })

    return True


def is_ready(task: dict[str, Any], all_tasks: list[dict[str, Any]]) -> bool:
    """
    Return True when *task* is pending and has no unresolved blockers.

    A blocker is unresolved when it exists and is not yet completed.
    """
    if task["status"] != "pending":
        return False
    incomplete_ids = {t["id"] for t in all_tasks if t["status"] != "completed"}
    return not any(b in incomplete_ids for b in task["blocked_by"])


# ── Task mode switch (V1 TodoWrite vs V2 Task graph) ──────────────────────────

_current_task_mode: str = "task"


def get_task_mode() -> str:
    return _current_task_mode


def set_task_mode(mode: str) -> None:
    global _current_task_mode
    _current_task_mode = mode


def is_task_mode_enabled() -> bool:
    return _current_task_mode == "task"


def is_todo_mode_enabled() -> bool:
    return _current_task_mode == "todo"


# ── Minimal task tools ────────────────────────────────────────────────────────


class TaskCreateTool:
    name = "TaskCreate"

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        task_list_id = get_task_list_id(context.get("session_id") or "default")
        id = await create_task(task_list_id, {
            "subject": input.get("subject", ""),
            "description": input.get("description", ""),
            "active_form": input.get("active_form"),
            "metadata": input.get("metadata"),
        })
        return {"content": f"Task #{id} created: {input.get('subject', '')}"}


class TaskListTool:
    name = "TaskList"

    async def call(self, _input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        task_list_id = get_task_list_id(context.get("session_id") or "default")
        all_tasks = await list_tasks(task_list_id)
        if not all_tasks:
            return {"content": "No tasks found"}

        resolved_ids = {t["id"] for t in all_tasks if t["status"] == "completed"}
        lines = []
        for task in sorted(all_tasks, key=lambda t: int(t["id"]) if t["id"].isdigit() else 0):
            open_blockers = [b for b in task["blocked_by"] if b not in resolved_ids]
            blocker_suffix = (
                f" [blocked by {', '.join('#' + b for b in open_blockers)}]"
                if open_blockers
                else ""
            )
            lines.append(f"#{task['id']} [{task['status']}] {task['subject']}{blocker_suffix}")
        return {"content": "\n".join(lines)}


class TaskGetTool:
    name = "TaskGet"

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        task_list_id = get_task_list_id(context.get("session_id") or "default")
        task = await get_task(task_list_id, input.get("task_id", ""))
        if task is None:
            return {"content": "Task not found", "is_error": True}

        lines = [
            f"Task #{task['id']}: {task['subject']}",
            f"Status: {task['status']}",
            f"Description: {task['description']}",
        ]
        if task.get("active_form"):
            lines.append(f"ActiveForm: {task['active_form']}")
        if task["blocked_by"]:
            lines.append(f"Blocked by: {', '.join('#' + b for b in task['blocked_by'])}")
        if task["blocks"]:
            lines.append(f"Blocks: {', '.join('#' + b for b in task['blocks'])}")
        return {"content": "\n".join(lines)}


class TaskUpdateTool:
    name = "TaskUpdate"

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        task_list_id = get_task_list_id(context.get("session_id") or "default")
        task_id: str = input.get("task_id", "")

        if input.get("status") == "deleted":
            ok = await delete_task(task_list_id, task_id)
            if ok:
                return {"content": f"Task #{task_id} deleted."}
            return {"content": f"Failed to delete task #{task_id}.", "is_error": True}

        updates: dict[str, Any] = {}
        for field in ("subject", "description", "active_form", "status"):
            if isinstance(input.get(field), str):
                updates[field] = input[field]
        if isinstance(input.get("metadata"), dict):
            updates["metadata"] = input["metadata"]

        updated = await update_task(task_list_id, task_id, updates)
        if updated is None:
            return {"content": "Task not found", "is_error": True}

        # Add blocking relationships.
        if isinstance(input.get("add_blocks"), list):
            for downstream_id in input["add_blocks"]:
                await block_task(task_list_id, task_id, downstream_id)
        if isinstance(input.get("add_blocked_by"), list):
            for upstream_id in input["add_blocked_by"]:
                await block_task(task_list_id, upstream_id, task_id)

        return {"content": f"Updated task #{task_id}"}


# Singleton instances
task_create_tool = TaskCreateTool()
task_list_tool = TaskListTool()
task_get_tool = TaskGetTool()
task_update_tool = TaskUpdateTool()
