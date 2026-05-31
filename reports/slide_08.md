---
title: "Startup: Bootstrap Sequence"
slide: "08"
section: "Entry Point & Bootstrap"
date: "2026-05-31"
---

# Startup: Bootstrap Sequence

1. **`load_env()`** — loads `.env` + `~/.claude.json` + `~/.claude/settings.json` into process environment (`utils/load_env.py`)

2. **`bootstrap_skills()`** — scans `~/.agent-butler/skills/*.md` and `./.agent-butler/skills/*.md`; parses YAML frontmatter; builds the skill registry with dynamic + conditional entries (`services/skills/bootstrap.py`)

3. **`bootstrap_mcp()`** — reads `mcpServers` from `settings.json`; connects to each server (stdio/http/SSE); calls `list_tools()`; wraps discovered tools as native `Tool` objects with `mcp__` prefix; registers them in `_mcp_tools` (`services/mcp/bootstrap.py`)

4. **`register_builtin_tools([...])`** — registers all 16 built-in tools in `_builtin_tools` (`tools/registry.py`)

5a. **Interactive mode** → create `App` instance → `app.run()` starts the async REPL

5b. **Print mode** → create `SessionController` → `submit(message)` → print response → exit

6. **Teardown** → `disconnect_all()` closes all MCP server connections

---

**Why order matters**

The system prompt is assembled at turn time, after all tools are registered. Tools registered late would be missing from the prompt.

---

*Speaker notes: The bootstrap order is important. MCP connections are established eagerly at startup — not lazily per-turn — to keep turn latency predictable. Skills are parsed once; the registry is read-only during a session.*
