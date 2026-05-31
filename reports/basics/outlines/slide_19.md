---
title: "Sub-Agents: Delegation & Isolation"
slide: "19"
section: "Extensions & Integrations"
date: "2026-05-31"
---

# Sub-Agents: Delegation & Isolation

**`AgentDefinition` dataclass** (`agents/types.py`)

```python
@dataclass
class AgentDefinition:
    agent_type: str          # e.g. "explore", "code-reviewer"
    description: str         # shown to parent Claude
    system_prompt: str       # sub-agent's instructions
    model: str | None        # optional model override
    tools_allow: list[str]   # tool whitelist
    tools_deny: list[str]    # tool blacklist
    isolation: str           # "none" | "worktree"
    max_turns: int           # default 100
```

---

**Two execution modes**

| Mode | Behaviour | Return |
|------|-----------|--------|
| **Foreground** | Blocks until complete | Result inline |
| **Background** | Returns immediately | `agent_id`; completion injected into next user turn |

---

**Isolation options**

```
isolation = "none"
  -> shares main working directory
  -> suitable for read-only tasks

isolation = "worktree"
  -> creates isolated git worktree  (utils/worktree.py)
  -> agent's file mutations are fully isolated
  -> worktree auto-removed if unchanged on completion
```

---

**Built-in agents** (`agents/built_in/`)

| Agent | Tools | Purpose |
|-------|-------|---------|
| `explore` | Read, Grep, Glob only | Safe read-only exploration |
| `general_purpose` | Full tool access | General delegation |

Custom agents: JSON files in `~/.easy-agent/agents/` or `./.easy-agent/agents/`

---

**Parallel agent pattern**

```
parent agent
  |
  +-- AgentTool(type="explore", isolation="worktree")  -> branch-A
  |
  +-- AgentTool(type="explore", isolation="worktree")  -> branch-B
  |
  +-- AgentTool(type="explore", isolation="worktree")  -> branch-C
  |
  <- results injected at next turn; parent coordinates merge
```

**Source:** `agents/types.py`, `agents/run_agent.py`, `agents/run_async_agent.py`, `utils/worktree.py`

---

*Speaker notes: Worktree isolation is powerful for parallelism. Multiple agents can each work on their own branch simultaneously. The parent agent coordinates and merges. Background agents are notified via the notification store — the parent sees an "AGENT_COMPLETE" banner at the start of the next turn.*
