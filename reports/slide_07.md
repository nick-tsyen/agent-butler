---
title: "CLI Flags & Entry Point"
slide: "07"
section: "Entry Point & Bootstrap"
date: "2026-05-31"
---

# CLI Flags & Entry Point

**Call chain**

```
agent-butler (CLI)
  └─→ agent_butler/cli.py : main()
        └─→ asyncio.run(_async_main(args))
```

---

**Flags**

| Flag | Effect |
|------|--------|
| `--model claude-opus-4` | Override the model for this session |
| `--plan` | Read-only mode — only Read/Grep/Glob/Bash-read allowed |
| `--auto` | All operations auto-approved, no prompts |
| `--resume SESSION_ID` | Resume a previous conversation from its JSONL file |
| `--cwd /path/to/project` | Change working directory before starting |
| `--print "question"` | Non-interactive; print response to stdout and exit |

---

**Two runtime modes**

- **Interactive mode** (default): Rich TUI REPL, streaming responses, live tool cards
- **Print mode** (`--print`): stdout only, no TUI; combine with `--auto` for CI/scripting

---

**Example: CI invocation**

```bash
agent-butler --print "Summarise recent changes" --auto --cwd /path/to/repo
```

---

*Speaker notes: The --print + --auto combination makes Agent Butler scriptable — it is the equivalent of curl for Claude. Fire a question at your codebase and get a structured answer back on stdout. The --plan flag is great for onboarding: let Claude explore the codebase and explain it without the risk of it touching any files.*
