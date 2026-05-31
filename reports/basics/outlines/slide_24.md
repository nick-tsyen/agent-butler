---
title: "State & Persistence: Five Stores"
slide: "24"
section: "Platform Services"
date: "2026-05-31"
---

# State & Persistence: Five Stores

## Store Reference

| Store | Location | Format | Scope | Concurrency |
|-------|----------|--------|-------|-------------|
| `task_store.py` | `~/.easy-agent/tasks/<list>/` | File-locked JSON, one file per task | Cross-session, persistent | `filelock` FileLock |
| `session/storage.py` | `~/.easy-agent/projects/<cwd>/sessions/` | JSONL, one line per message/event | Per-session, resumable via `--resume` | Single writer |
| `todo_store.py` | In-memory | List of `TodoItem` Pydantic models | Current session only | Single-threaded |
| `notification_store.py` | In-memory queue | List of notification objects | Current session, background agents | asyncio queue |
| `async_agent_store.py` | In-memory dict | `agent_id → AgentRunResult` | Current session, background agents | asyncio dict |

## Key Behaviours

- **Session resumption**: `--resume SESSION_ID` replays the JSONL file line-by-line into `messages[]` — the full conversation is reconstructed
- **Background agent notifications**: when a background agent completes, it enqueues a notification; at the start of the next user turn, notifications are injected as system messages
- **Task persistence**: tasks survive session restarts — they're the mechanism for long-running cross-session work

## Source Files

`state/task_store.py`, `session/storage.py`, `state/todo_store.py`, `state/notification_store.py`, `state/async_agent_store.py`

---

*Speaker notes: The distinction between tasks and todos matters. Todos are in-memory checklists for the current session — ephemeral, used by Claude to track progress on the current request. Tasks are persistent, file-backed, and survive session restarts — used for multi-session projects.*
