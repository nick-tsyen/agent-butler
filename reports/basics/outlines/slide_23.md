---
title: "Context Management: System Prompt & Compaction"
slide: "23"
section: "Platform Services"
date: "2026-05-31"
---

# Context Management: System Prompt & Compaction

## System Prompt Assembly (`context/system_prompt.py`)

Assembled fresh at the start of every turn from:

| Component | Source |
|-----------|--------|
| Static core instructions | Hardcoded: tool usage rules, workspace boundaries |
| Git context | Branch, status, recent commit (if git repo detected) |
| Environment | OS, CWD, current date |
| `AGENT.md` content | `~/.easy-agent/AGENT.md` + project `.easy-agent/AGENT.md` |
| Tool definitions | Generated from `get_all_tools()` registry |
| Skill descriptions | From skill registry (dynamic + active conditional skills) |
| Agent descriptions | From agent registry |

## Auto-Compaction (`context/auto_compact.py`)

```
Token usage monitored per turn (utils/tokens.py)
  → 80% of context window → warn user: "Context getting long"
  → 95% of context window → trigger compaction:
       context/compaction.py sends conversation to Claude
       asking it to produce a summary → replace history
       with summary + last N turns → session continues
```

## Memory System (`context/memory/`)

- Persistent `.md` files in `~/.easy-agent/projects/<cwd>/memory/`
- Written by `MemoryWriteTool`
- `find_relevant.py`: retrieve contextually relevant memories for the current turn
- Memories are injected into the system prompt when relevant

---

*Speaker notes: The system prompt is assembled dynamically — tool descriptions, skill descriptions, and agent descriptions are all generated at call time. This means adding a new tool or skill immediately affects what Claude knows about its capabilities, without any additional configuration.*
