---
title: "Technology Stack"
slide: "05"
section: "High-Level Architecture"
date: "2026-05-31"
---

# Technology Stack

**Python requirement: 3.11+**

| Library | Version | Role |
|---------|---------|------|
| `anthropic` | >= 0.40.0 | Anthropic SDK; SSE streaming API |
| `asyncio` | stdlib | All I/O is async; `gather()` for parallel tools |
| `pydantic` | >= 2.0.0 | Type validation and serialisation for all models |
| `rich` | >= 13.0.0 | Terminal UI: panels, markdown, live updates, spinners |
| `prompt_toolkit` | >= 3.0.0 | Interactive input with history and completion |
| `mcp` | >= 1.0.0 | Model Context Protocol client |
| `filelock` | >= 3.13.0 | File-locked task store (multi-process safe) |
| `aiofiles` | >= 24.0.0 | Non-blocking async file I/O |
| `pyyaml` | >= 6.0 | YAML frontmatter parsing for skills |
| `python-dotenv` | >= 1.0.0 | `.env` and `~/.claude.json` env loading |

---

**Why each dependency matters**

- `asyncio` is the concurrency model for the entire system — no threads anywhere, every I/O operation is awaited
- `pydantic` v2 is used for every data structure that crosses a layer boundary, giving strong runtime guarantees
- `rich` provides the full TUI experience: live streaming panels, markdown rendering, and spinner animations
- `filelock` ensures the task store is safe when multiple processes access the same task list simultaneously

---

*Speaker notes: The stack is deliberately small and well-chosen. asyncio is the threading model for the whole system — no threads, everything is async. Pydantic v2 is used for every data structure that crosses a layer boundary, which means serialisation errors surface immediately at the boundary rather than deep inside business logic.*
