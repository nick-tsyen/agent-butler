---
title: "How to Extend Easy Agent"
slide: "20"
section: "Extensions & Integrations"
date: "2026-05-31"
---

# How to Extend Easy Agent

Four extension patterns — each targets a different layer of the platform.

---

### Add a Custom Tool

```python
# 1. Subclass Tool in tools/my_tool.py
class MyTool(Tool):
    async def call(self, input_data, context):
        ...
        return ToolResult(output="done")

    def is_read_only(self): return False
    def is_concurrency_safe(self): return False
    def is_enabled(self): return True

# 2. Register at bootstrap (cli.py)
register_builtin_tools([MyTool()])
```

Tool name and schema auto-appear in the system prompt after registration.

---

### Add a Skill

- [ ] Create `~/.easy-agent/skills/my-skill.md`
- [ ] Add YAML frontmatter: `name`, `description`, optional `allowedTools`, `budget`, `paths`
- [ ] No code change required — auto-discovered at startup

---

### Add a Custom Agent

- [ ] Create `~/.easy-agent/agents/my-agent.json`
- [ ] Populate `AgentDefinition` fields: `agent_type`, `system_prompt`, `tools_allow`, `isolation`
- [ ] Reference via `agent_type` in `AgentTool` calls

---

### Connect an MCP Server

- [ ] Add entry to `mcpServers` in `~/.easy-agent/settings.json`
- [ ] Specify `command`, `args`, `transport`
- [ ] Restart Easy Agent — tools auto-appear with `mcp__<server>__` prefix

---

**Decision guide**

```
Need new capability (code required)?    -> Custom Tool
Need a reusable workflow (no code)?     -> Skill
Need scoped / isolated delegation?      -> Custom Agent
Need an external integration?           -> MCP Server
```

---

*Speaker notes: The four extension points cover 99% of customisation needs. Tools are for new capabilities. Skills are for reusable workflows. Agents are for scoped delegation. MCP is for external integrations. Start with a skill; escalate to a tool only if you need code.*
