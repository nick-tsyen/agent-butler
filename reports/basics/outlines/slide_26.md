---
title: "Developer Guide: Extension Patterns"
slide: "26"
section: "Testing & Development"
date: "2026-05-31"
---

# Developer Guide: Extension Patterns

## 1. Add a Custom Tool

- [ ] Create `tools/my_tool.py`, subclass `Tool(ABC)` from `tools/base.py`
- [ ] Implement `call()`, `is_read_only()`, `is_concurrency_safe()`, `is_enabled()`
- [ ] Define `name` and `description` properties (used in system prompt)
- [ ] Define `input_schema` (JSON Schema dict — sent to Claude as tool definition)
- [ ] In `easy_agent/cli.py` bootstrap: `register_builtin_tools([MyTool()])`
- [ ] The tool name and schema appear in the system prompt on next run

## 2. Add a Skill

- [ ] Create `~/.easy-agent/skills/my-skill.md`
- [ ] YAML frontmatter: at minimum `name` and `description`
- [ ] Optionally add `allowedTools`, `budget`, `paths`
- [ ] No code change needed — auto-discovered at startup via `services/skills/load_skills_dir.py`

## 3. Add a Custom Agent

- [ ] Create `~/.easy-agent/agents/my-agent.json`
- [ ] Fill `AgentDefinition` fields: `agent_type`, `description`, `system_prompt`, `tools_allow`, `isolation`
- [ ] Optionally set `model` for a different Claude tier
- [ ] Claude invokes it via `AgentTool` using the `agent_type` string

## 4. Connect an MCP Server

- [ ] Add entry to `mcpServers` in `~/.easy-agent/settings.json`
- [ ] Specify: `command`, `args`, `transport` (`stdio` | `http` | `sse`)
- [ ] Optionally pass `env` for environment variables (API keys, etc.)
- [ ] Restart — tools appear automatically as `mcp__<server>__<tool>`

---

*Speaker notes: Start with a skill — zero code, instant iteration. Move to a tool when you need Python logic. Use agents when you need scoped delegation or tool restrictions. Use MCP for anything that lives outside this codebase.*
