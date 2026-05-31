"""
Step 9 - Session persistence with JSONL transcripts

Goal:
- persist a conversation as append-only JSONL
- group sessions by project
- restore messages from disk after process restart
- list recent sessions for the current project

This file keeps the core ideas in one place for learning.
The production code in src/session/* is more complete.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles

# ── Constants ─────────────────────────────────────────────────────────────────

AGENT_BUTLER_HOME: Path = Path.home() / ".agent-butler"
PROJECTS_DIR: Path = AGENT_BUTLER_HOME / "projects"
MAX_SESSIONS: int = 20


# ── Usage helpers ─────────────────────────────────────────────────────────────


def create_empty_usage() -> dict[str, int]:
    """Return a zeroed usage dict."""
    return {"input_tokens": 0, "output_tokens": 0}


# ── Session identifiers ────────────────────────────────────────────────────────


def create_session_id() -> str:
    """Generate a unique session identifier (UUID v4)."""
    return str(uuid.uuid4())


def get_project_hash(cwd: str) -> str:
    """
    Hash the absolute project path to a 16-character hex string.
    Every workspace gets its own folder in PROJECTS_DIR.
    """
    return hashlib.sha256(os.path.abspath(cwd).encode()).hexdigest()[:16]


def get_session_paths(cwd: str, session_id: str) -> dict[str, Path]:
    """Return all relevant filesystem paths for a session."""
    project_hash = get_project_hash(cwd)
    project_dir = PROJECTS_DIR / project_hash
    return {
        "root_dir": AGENT_BUTLER_HOME,
        "project_dir": project_dir,
        "transcript_path": project_dir / f"{session_id}.jsonl",
        "latest_path": project_dir / "latest",
    }


async def _ensure_session_dir(paths: dict[str, Path]) -> None:
    """Create the project directory if it doesn't exist."""
    paths["project_dir"].mkdir(parents=True, exist_ok=True)


# ── Transcript entry constructors ─────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def create_session_meta_entry(
    *, session_id: str, cwd: str, started_at: str, model: str
) -> dict[str, Any]:
    """First line written to a transcript — identifies the session."""
    return {
        "type": "session_meta",
        "session_id": session_id,
        "cwd": cwd,
        "started_at": started_at,
        "model": model,
    }


def create_message_entry(
    *, role: str, message: dict[str, Any], timestamp: str | None = None
) -> dict[str, Any]:
    """Wrap a conversation message with metadata for the transcript."""
    return {
        "type": "message",
        "timestamp": timestamp or _now_iso(),
        "role": role,
        "message": message,
    }


def create_tool_event_entry(
    *,
    name: str,
    phase: str,
    result_length: int | None = None,
    is_error: bool | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Record a tool invocation event (start or done)."""
    entry: dict[str, Any] = {
        "type": "tool_event",
        "timestamp": timestamp or _now_iso(),
        "name": name,
        "phase": phase,
    }
    if result_length is not None:
        entry["result_length"] = result_length
    if is_error is not None:
        entry["is_error"] = is_error
    return entry


def create_usage_entry(
    *, turn: dict[str, int], total: dict[str, int], timestamp: str | None = None
) -> dict[str, Any]:
    """Record token usage for a turn."""
    return {
        "type": "usage",
        "timestamp": timestamp or _now_iso(),
        "turn": turn,
        "total": total,
    }


def create_system_entry(
    *, level: str, message: str, timestamp: str | None = None
) -> dict[str, Any]:
    """Record a system-level log line (info or error)."""
    return {
        "type": "system",
        "timestamp": timestamp or _now_iso(),
        "level": level,
        "message": message,
    }


# ── Transcript I/O ─────────────────────────────────────────────────────────────


async def init_session_storage(
    *,
    session_id: str,
    cwd: str,
    started_at: str,
    model: str,
) -> dict[str, Path]:
    """
    Initialise the on-disk storage for a new session.

    Writes the session_meta entry and updates the latest pointer.
    """
    paths = get_session_paths(cwd, session_id)
    await _ensure_session_dir(paths)

    meta = create_session_meta_entry(
        session_id=session_id, cwd=cwd, started_at=started_at, model=model
    )
    async with aiofiles.open(paths["transcript_path"], "a", encoding="utf-8") as f:
        await f.write(json.dumps(meta) + "\n")

    async with aiofiles.open(paths["latest_path"], "w", encoding="utf-8") as f:
        await f.write(session_id + "\n")

    return paths


async def append_transcript_entry(
    cwd: str, session_id: str, entry: dict[str, Any]
) -> None:
    """Append one JSONL record to the session transcript."""
    paths = get_session_paths(cwd, session_id)
    await _ensure_session_dir(paths)

    async with aiofiles.open(paths["transcript_path"], "a", encoding="utf-8") as f:
        await f.write(json.dumps(entry) + "\n")

    async with aiofiles.open(paths["latest_path"], "w", encoding="utf-8") as f:
        await f.write(session_id + "\n")


# ── Parse helpers ──────────────────────────────────────────────────────────────


def _is_usage(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("input_tokens"), int)
        and isinstance(value.get("output_tokens"), int)
    )


def _is_message_param(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("role") in ("user", "assistant")
        and "content" in value
    )


def parse_json_line(line: str) -> dict[str, Any] | None:
    """
    Parse one JSONL line and validate it matches a known entry type.

    Returns None for malformed lines so a bad line does not crash restore.
    """
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError:
        return None

    t = parsed.get("type")

    if t == "session_meta":
        return {
            "type": "session_meta",
            "session_id": parsed.get("session_id"),
            "cwd": parsed.get("cwd"),
            "started_at": parsed.get("started_at"),
            "model": parsed.get("model"),
        }

    if (
        t == "message"
        and isinstance(parsed.get("timestamp"), str)
        and parsed.get("role") in ("user", "assistant")
        and _is_message_param(parsed.get("message"))
    ):
        return parsed

    if (
        t == "tool_event"
        and isinstance(parsed.get("timestamp"), str)
        and isinstance(parsed.get("name"), str)
        and parsed.get("phase") in ("start", "done")
    ):
        return parsed

    if (
        t == "usage"
        and isinstance(parsed.get("timestamp"), str)
        and _is_usage(parsed.get("turn"))
        and _is_usage(parsed.get("total"))
    ):
        return parsed

    if (
        t == "system"
        and isinstance(parsed.get("timestamp"), str)
        and parsed.get("level") in ("info", "error")
        and isinstance(parsed.get("message"), str)
    ):
        return parsed

    return None


async def read_transcript_entries(file_path: Path) -> list[dict[str, Any]]:
    """Read and parse all valid entries from a transcript file."""
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        raw = await f.read()

    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = parse_json_line(line)
        if parsed:
            entries.append(parsed)
    return entries


async def get_latest_session_id(cwd: str) -> str | None:
    """Read the latest session ID from the project's latest pointer file."""
    paths = get_session_paths(cwd, "placeholder")
    try:
        async with aiofiles.open(paths["latest_path"], encoding="utf-8") as f:
            value = (await f.read()).strip()
        return value or None
    except FileNotFoundError:
        return None


# ── Session restore ────────────────────────────────────────────────────────────


def _get_last_updated_at(entries: list[dict[str, Any]], fallback: str) -> str:
    """Return the timestamp of the most recent timed entry, or *fallback*."""
    for entry in reversed(entries):
        if isinstance(entry.get("timestamp"), str):
            return entry["timestamp"]
    return fallback


async def restore_session(cwd: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Restore a previous session from disk.

    When *session_id* is None, the latest session for the project is used.
    Raises ValueError if no session can be found or the transcript is empty.
    """
    resolved_id = session_id or await get_latest_session_id(cwd)
    if not resolved_id:
        raise ValueError("No saved session found for this project.")

    paths = get_session_paths(cwd, resolved_id)
    entries = await read_transcript_entries(paths["transcript_path"])
    if not entries:
        raise ValueError("Session is empty or unreadable.")

    meta = next((e for e in entries if e.get("type") == "session_meta"), None)
    if not meta:
        raise ValueError("Session is missing session metadata.")

    messages = [e["message"] for e in entries if e.get("type") == "message"]

    latest_usage_entry = next(
        (e for e in reversed(entries) if e.get("type") == "usage"), None
    )

    return {
        "summary": {
            "session_id": meta["session_id"],
            "cwd": meta["cwd"],
            "started_at": meta["started_at"],
            "updated_at": _get_last_updated_at(entries, meta["started_at"]),
            "model": meta["model"],
            "message_count": len(messages),
            "total_usage": latest_usage_entry["total"] if latest_usage_entry else create_empty_usage(),
        },
        "messages": messages,
    }


# ── Session listing ────────────────────────────────────────────────────────────


async def list_project_sessions(
    cwd: str, limit: int = MAX_SESSIONS
) -> list[dict[str, Any]]:
    """Return summaries of recent sessions for the current project, newest first."""
    paths = get_session_paths(cwd, "placeholder")
    project_dir = paths["project_dir"]

    try:
        dir_entries = list(project_dir.iterdir())
    except FileNotFoundError:
        return []

    session_files = [
        e for e in dir_entries if e.is_file() and e.suffix == ".jsonl"
    ]

    summaries: list[dict[str, Any]] = []
    for file_path in session_files:
        entries = await read_transcript_entries(file_path)
        meta = next((e for e in entries if e.get("type") == "session_meta"), None)
        if not meta:
            continue

        messages = [e for e in entries if e.get("type") == "message"]
        latest_usage = next((e for e in reversed(entries) if e.get("type") == "usage"), None)

        summaries.append({
            "session_id": meta["session_id"],
            "cwd": meta["cwd"],
            "started_at": meta["started_at"],
            "updated_at": _get_last_updated_at(entries, meta["started_at"]),
            "model": meta["model"],
            "message_count": len(messages),
            "total_usage": latest_usage["total"] if latest_usage else create_empty_usage(),
        })

    # Sort newest-first and apply the limit.
    summaries.sort(key=lambda s: s["updated_at"], reverse=True)
    return summaries[:limit]


async def format_project_session_history(cwd: str) -> str:
    """Return a human-readable summary of recent sessions for the project."""
    sessions = await list_project_sessions(cwd)
    if not sessions:
        return "No saved sessions found for this project."

    lines = ["Recent sessions:"]
    for s in sessions:
        total = s["total_usage"]["input_tokens"] + s["total_usage"]["output_tokens"]
        lines.append(
            "\n".join([
                f"- {s['session_id']}",
                f"  Updated: {s['updated_at']}",
                f"  Started: {s['started_at']}",
                f"  Messages: {s['message_count']}",
                (
                    f"  Usage: {s['total_usage']['input_tokens']} in / "
                    f"{s['total_usage']['output_tokens']} out / {total} total"
                ),
                f"  Model: {s['model']}",
            ])
        )

    return "\n".join(lines)
