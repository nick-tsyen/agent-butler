---
title: "Key Use Cases"
slide: "03"
section: "Introduction"
date: "2026-05-31"
---

# Key Use Cases

---

**1. Interactive dev assistance**

Run `agent-butler` in a repo; ask Claude to find bugs, refactor, or explain code. Claude reads files, runs tests, and edits code in real time. No copy-pasting — it operates directly on the working tree.

---

**2. Automated task pipelines**

```bash
agent-butler --print "Summarise recent changes" --auto --cwd /path/to/repo
```

`--print` returns the response to stdout; `--auto` skips all permission prompts. Scriptable and CI-friendly. Combine with `--cwd` to point at any directory.

---

**3. Extensible platform**

| Extension point | How to add it |
|----------------|---------------|
| Custom tool | Subclass `Tool`; drop into `tools/` |
| Skill | Drop a `.md` file into `~/.agent-butler/skills/` |
| Agent | Add a JSON definition to `~/.agent-butler/agents/` |
| MCP server | Register in `settings.json` under `mcpServers` |

No changes to core code required.

---

**Bonus modes**

- `--plan` — read-only walkthrough; no writes allowed; safe for onboarding and exploration
- `--resume SESSION_ID` — replay a JSONL session file to continue a previous conversation

---

*Speaker notes: The `--print --auto` combo is particularly useful for wrapping Claude in shell scripts or CI pipelines. The extensibility story is a key differentiator — you can extend the agent at every layer (tools, skills, agents, servers) without forking the core. The --plan flag is a safe way to let Claude explore an unfamiliar codebase without touching anything.*
