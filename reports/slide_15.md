---
title: "Built-in Tools: All 16"
slide: "15"
section: "Tool System"
date: "2026-05-31"
---

# Built-in Tools: All 16

| Tool | Read-Only | Concurrency-Safe | Description |
|------|:---------:|:----------------:|-------------|
| `Read` | Yes | Yes | Read file contents with optional line ranges |
| `Glob` | Yes | Yes | Match files by glob pattern |
| `Grep` | Yes | Yes | Search file contents with regex |
| `Bash` | Varies | Varies | Execute shell commands (sandboxed on macOS) |
| `Write` | No | No | Create or overwrite files |
| `Edit` | No | No | Find-replace editing within a file |
| `Agent` | Varies | Yes | Delegate to a sub-agent |
| `Skill` | No | No | Invoke a named skill |
| `TodoWrite` | No | No | Manage the in-memory session checklist |
| `TaskCreate` | No | No | Create a persistent task (file-backed) |
| `TaskUpdate` | No | No | Update task status or metadata |
| `TaskGet` | No | No | Retrieve a task by ID |
| `TaskList` | No | No | List all tasks |
| `EnterPlanMode` | No | No | Switch session to read-only plan mode |
| `ExitPlanMode` | No | No | Restore full permissions |
| `MemoryWrite` | No | No | Append to persistent project memory |

---

**Callouts**

- `AgentTool` is concurrency-safe even though it does work — it runs in an isolated scope
- `SkillTool` injects a skill's system prompt mid-conversation
- `EnterPlanMode` / `ExitPlanMode` allow Claude itself to manage its own permission mode

---

**Source layout**

```
tools/
  read_tool.py
  glob_tool.py
  grep_tool.py
  bash_tool.py
  write_tool.py
  edit_tool.py
  agent_tool.py
  skill_tool.py
  todo_write_tool.py
  task_create_tool.py
  task_update_tool.py
  task_get_tool.py
  task_list_tool.py
  enter_plan_mode_tool.py
  exit_plan_mode_tool.py
  memory_write_tool.py
```

One `*_tool.py` file per tool.

---

*Speaker notes: 16 tools cover the full surface Claude needs: read, write, search, execute, delegate, and manage state. The task tools (Create/Update/Get/List) are for long-running multi-session work. MemoryWrite lets Claude persist insights across sessions.*
