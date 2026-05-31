---
title: "Terminal UI: Rich Live + UIEvents"
slide: "22"
section: "Platform Services"
date: "2026-05-31"
---

# Terminal UI: Rich Live + UIEvents

## Architecture Overview

```
App (ui/app.py)
  └─ creates SessionController
  └─ runs async REPL
  └─ dispatches slash commands (/help, /clear, /cost, /model, /tasks, ...)
        │
        ▼
SessionController (ui/session_hook.py — 395 lines)
  └─ yields UIEvent objects
        │
        ▼
App._process_event()
  └─ _layout.add_event()
        └─ Rich Live.refresh()
```

## `UIEvent` Types (`ui/events.py`)

| Event | Purpose |
|-------|---------|
| `UISpinnerStart` | Show thinking indicator |
| `UITextDelta` | Stream text to conversation view |
| `UIToolStart` | Show tool card with input |
| `UIToolDone` | Update tool card with output |
| `UIPermissionRequest` | Show inline approval prompt |
| `UITurnComplete` | Finalise turn, show usage stats |
| `UIError` | Display error banner |

## `TUILayout` Components (`ui/layout.py`)

- `ConversationView` — markdown-rendered message history
- `ToolCard` — live tool invocation card with collapsible input/output
- `TodoListView` — session-level checklist (from `TodoWrite` tool)
- `TaskListView` — persistent task graph
- `StatusBar` — model name, permission mode, cumulative token usage
- `Spinner` — breathing-star + shimmer animation while streaming

## Performance

`StreamingBuffer` in `ui/layout.py`: throttles Rich `Live.refresh()` to ~30ms intervals to prevent CPU thrashing.

## Input

`ui/input_prompt.py` — `prompt_toolkit` multi-line input with persistent history file.

---

*Speaker notes: The UIEvent protocol is the clean interface between the session controller and the UI layer. The session controller never knows what kind of UI it's talking to — it just emits events. This makes it testable and in theory swappable for a web or IDE UI.*
