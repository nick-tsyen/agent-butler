---
title: "On-Disk State Layout"
slide: "06"
section: "High-Level Architecture"
date: "2026-05-31"
---

# On-Disk Layout: `~/.agent-butler/`

```
~/.agent-butler/
├── settings.json              # Permissions, MCP servers, sandbox config
├── AGENT.md                   # User-scope system prompt additions
│
├── tasks/
│   └── <list_id>/
│       ├── <task_id>.json     # One file per task (file-locked)
│       └── .lock
│
├── plans/                     # Temporary plan files for multi-step tasks
│
├── projects/
│   └── <encoded_cwd>/
│       ├── sessions/
│       │   └── <id>.jsonl     # Conversation history (resumable)
│       ├── memory/
│       │   └── *.md           # Persistent project memories
│       └── tasks/
│           └── *_output.txt   # Sub-agent output files
│
├── skills/
│   └── *.md                   # User-scope skill definitions
│
├── agents/
│   └── *.json                 # Custom agent definitions
│
└── worktrees/
    └── <name>/                # Isolated git worktrees for sub-agents
```

---

**Key design choices**

- Everything is file-based — no database, no background daemon
- Project-scope overrides live at `./.agent-butler/` (settings, skills, agents)
- Path encoding (CWD to filesystem-safe name) is centralised in `utils/paths.py`
- The JSONL session format makes sessions trivially resumable: replay the lines to restore state

---

*Speaker notes: Everything is file-based — no database, no daemon. The JSONL session format makes sessions trivially resumable: just replay the lines to reconstruct conversation history. Path encoding converts the current working directory to a filesystem-safe name, handled centrally in utils/paths.py so every subsystem derives paths consistently.*
