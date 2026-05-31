---
title: "Agent Butler Python Harness — Presentation Deck Outline"
date: "2026-05-31"
time: "00:00"
audience: "Engineers / Developers"
purpose: "Knowledge sharing / Onboarding + Architecture Review"
slide_count: 28
status: draft
---

# Presentation Deck Outline: Agent Butler Python Harness

This outline maps every slide in the 28-slide deck. Each entry lists the slide's title, the key content points to cover, and the source files to draw from. Individual slide files (`slide_01.md` … `slide_28.md`) will be created after this outline is approved.

---

## Section 1 — Introduction (Slides 01–03)

### Slide 01 · Title

**Title:** Agent Butler: A Python Agent Harness

**Key content:**
- Deck subtitle: "Architecting a terminal-native AI coding agent with Claude"
- One-liner: "Agent Butler lets Claude reason, act, and observe — in a sandboxed, permission-controlled terminal environment"
- Context: Python port of a TypeScript codebase; ~9,100 lines across 85+ files

**Source files:** `README.md`, `pyproject.toml` (version, entry point)

---

### Slide 02 · What Is It?

**Title:** What Is Agent Butler?

**Key content:**
- Interactive multi-turn REPL: submit a question, get a streamed response, loop
- Tool execution: Claude can read/write files, run shell commands, search code
- Sub-agent delegation: spawn isolated agents for scoped tasks
- MCP integration: connect external tool servers via Model Context Protocol
- Skills system: reusable Markdown-defined workflows
- Sandbox isolation: macOS `sandbox-exec` profiles for safe shell execution
- Scale: 9,100 lines, 85+ files, fully async, Pydantic-typed throughout

**Source files:** `README.md`, `agent_butler/__init__.py`

---

### Slide 03 · Key Use Cases

**Title:** What Can You Do With It?

**Key content:**
- **Interactive dev assistance** — chat with Claude while it reads/edits your codebase in real time
- **Automated task pipelines** — run in `--print` mode from CI/scripts; combine with `--auto` for no permission prompts
- **Onboarding & exploration** — `--plan` mode for read-only codebase walkthroughs
- **Extensible platform** — drop in custom tools, skills, agents, or MCP servers without touching core code
- **Session continuity** — resume previous sessions by ID; persistent memory across sessions

**Source files:** `agent_butler/cli.py` (flags), `README.md`

---

## Section 2 — High-Level Architecture (Slides 04–06)

### Slide 04 · Five-Layer Architecture

**Title:** Architecture: Five Layers

**Key content:**
- ASCII/diagram of the five layers (top to bottom):
  1. **Interaction Layer** — Rich console, prompt_toolkit input, Live TUI updates (`ui/app.py`, `ui/layout.py`)
  2. **Orchestration Layer** — SessionController, multi-turn flow, command dispatch (`ui/session_hook.py`)
  3. **Core Agentic Loop** — Reason → Act → Observe, up to 100 turns (`core/agentic_loop.py`, `core/query_engine.py`)
  4. **Tooling Layer** — File ops, shell, search, delegation, skills, MCP tools (`tools/`, `services/`)
  5. **Model Communication Layer** — Anthropic SDK streaming, retry, JSON accumulation (`services/api/`)
- Each layer has a single responsibility; they communicate only downward

**Source files:** `core/agentic_loop.py`, `ui/app.py`, `ui/session_hook.py`, `tools/registry.py`, `services/api/streaming.py`

---

### Slide 05 · Technology Stack

**Title:** Technology Stack

**Key content:**
| Library | Role | Why chosen |
|---------|------|------------|
| `anthropic >= 0.40.0` | Anthropic SDK, streaming | Official SDK with SSE streaming |
| `asyncio` (stdlib) | Concurrency throughout | All I/O is async; `asyncio.gather()` for parallel tools |
| `pydantic >= 2.0.0` | Type validation & serialisation | All messages, tools, tasks, skills modelled as `BaseModel` |
| `rich >= 13.0.0` | Terminal UI rendering | Live panels, markdown, spinners |
| `prompt_toolkit >= 3.0.0` | Interactive input | History, multi-line input, completion |
| `mcp >= 1.0.0` | MCP client library | Connect external tool servers |
| `filelock >= 3.13.0` | Task store concurrency | Safe multi-process file access |
| `aiofiles >= 24.0.0` | Async file I/O | Non-blocking reads/writes |
| `pyyaml >= 6.0` | Skill frontmatter parsing | Skills are YAML-frontmattered Markdown |
| `python-dotenv >= 1.0.0` | Env loading | `.env` + `~/.claude.json` + settings JSON |

**Source files:** `pyproject.toml`

---

### Slide 06 · On-Disk State Layout

**Title:** On-Disk Layout: `~/.agent-butler/`

**Key content:**
```
~/.agent-butler/
├── settings.json          # Permissions, MCP servers, sandbox config
├── AGENT.md               # User-scope system prompt additions
├── tasks/<list_id>/       # Persistent task files (file-locked JSON)
├── plans/                 # Temporary plan files for multi-step tasks
├── projects/<cwd>/
│   ├── sessions/          # Conversation history (JSONL, resumable)
│   ├── memory/            # Project-level persistent Markdown memories
│   └── tasks/*_output.txt # Sub-agent output files
├── skills/*.md            # User-scope skill definitions
├── agents/*.json          # Custom agent definitions
└── worktrees/             # Isolated git worktrees for sub-agents
```
- Project-scope overrides: `./.agent-butler/settings.json`, `./.agent-butler/skills/`, `./.agent-butler/agents/`
- Path resolution centralised in `utils/paths.py`

**Source files:** `utils/paths.py`, `state/task_store.py`, `session/storage.py`

---

## Section 3 — Entry Point & Bootstrap (Slides 07–08)

### Slide 07 · CLI & Entry Point

**Title:** CLI Flags & Entry Point

**Key content:**
- Entry point: `agent-butler` → `agent_butler/cli.py:main()` → `asyncio.run(_async_main(args))`
- Key flags and their effect:

| Flag | Effect |
|------|--------|
| `--model claude-opus-4` | Override the model used |
| `--plan` | Read-only mode (only Read/Grep/Glob allowed) |
| `--auto` | All operations auto-allowed, no prompts |
| `--resume SESSION_ID` | Resume a previous conversation |
| `--cwd /path` | Change working directory before starting |
| `--print "question"` | Non-interactive, print response to stdout |

- `--print` + `--auto` = scriptable, CI-friendly invocation

**Source files:** `agent_butler/cli.py`, `agent_butler/__main__.py`

---

### Slide 08 · Bootstrap Sequence

**Title:** Startup: Bootstrap Sequence

**Key content:**
- Step-by-step initialisation order:
  1. `load_env()` — `.env` + `~/.claude.json` + `~/.claude/settings.json`
  2. `bootstrap_skills()` — scan `~/.agent-butler/skills/*.md` + project skills; parse YAML frontmatter; build skill registry
  3. `bootstrap_mcp()` — read `mcpServers` from `settings.json`; connect stdio/http/SSE transports; discover and wrap tools as native `Tool` objects
  4. `register_builtin_tools()` — register all 16 built-in tools
  5. **Interactive mode:** create `App` → run async REPL
     **Print mode:** create `SessionController` → submit message → print → exit
  6. Teardown: `disconnect_all()` MCP servers
- Why this order matters: tools must be registered before system prompt is assembled (prompt lists all available tools)

**Source files:** `cli.py`, `services/skills/bootstrap.py`, `services/mcp/bootstrap.py`, `tools/registry.py`

---

## Section 4 — Core Agentic Loop (Slides 09–11)

### Slide 09 · Reason → Act → Observe

**Title:** The Core Loop: Reason → Act → Observe

**Key content:**
- Central function: `async def query(...) -> AsyncGenerator[dict, None]` in `core/agentic_loop.py`
- Loop invariant: run until `stop_reason != "tool_use"` (max 100 turns)
- Each turn:
  1. **Reason** — stream `messages.stream()` to get Claude's response
  2. **Act** — extract all `ToolUseBlock` items from the response
  3. **Observe** — execute tools, append `tool_result` messages, loop back
- Yielded stream events:
  - `{"type": "text", "text": "..."}` — streaming text delta
  - `{"type": "tool_use_start", ...}` — tool card shown in UI
  - `{"type": "tool_execution_done", "results": [...]}` — tool outputs
  - `{"type": "result", ...}` — final message + cumulative usage stats

**Source files:** `core/agentic_loop.py` (289 lines), `core/query_engine.py`

---

### Slide 10 · Tool Batching: Concurrent vs Sequential

**Title:** Tool Execution: Batching Strategy

**Key content:**
- Not all tools are safe to run in parallel — some mutate files
- `is_concurrency_safe()` on `Tool` base class determines grouping
- **Concurrent batch** (`asyncio.gather()`): Read, Grep, Glob, Agent
- **Sequential batch**: Write, Edit, Bash, Skill, Task*, EnterPlanMode, ExitPlanMode, MemoryWrite
- Within a single Claude turn, tools are partitioned and groups execute in order: all concurrent first, then sequential one by one
- Benefit: multi-file reads complete in parallel (significant for large codebases)

**Source files:** `core/agentic_loop.py` (batch partitioning logic), `tools/base.py` (`is_concurrency_safe`)

---

### Slide 11 · End-to-End Turn Flow

**Title:** Full Turn: Sequence Diagram

**Key content:**
Sequence diagram (text or ASCII):
```
User types input
  → App._handle_submit(text)
    → SessionController.submit(text)
      → messages.append(UserMessage)
      → _run_agent_loop()
        → query() [async generator]
          → stream_message_with_retry()   [API call]
          → yield UIEvents (spinner, text deltas)
          → extract ToolUseBlocks
          → check_permission() per tool
            ↳ if needed: await on_permission_request (UI prompt)
          → tool.call(input, context)
          → yield UIToolDone events
          → messages.append(tool_results)
          → loop back (if stop_reason == "tool_use")
        → yield UITurnComplete
    → App._process_event()
      → _layout.add_event()
        → Rich Live.refresh()
```

**Source files:** `ui/app.py`, `ui/session_hook.py`, `core/agentic_loop.py`, `permissions/permissions.py`

---

## Section 5 — API & Streaming Layer (Slides 12–13)

### Slide 12 · Anthropic SDK Streaming

**Title:** Streaming: SSE Event Accumulation

**Key content:**
- `services/api/streaming.py`: wraps Anthropic SDK `.messages.stream()`
- SSE events are accumulated per-index (handles overlapping `tool_use` JSON)
- `StreamEvent` types emitted upstream:
  - `StreamMessageStartEvent` — message ID
  - `StreamTextEvent` — text delta
  - `StreamToolUseStartEvent` — tool name + ID
  - `StreamToolUseInputEvent` — partial JSON input
  - `StreamMessageDoneEvent` — final usage + stop reason
  - `StreamErrorEvent` — error events
- Per-index JSON accumulation: why it's needed (streaming tool input JSON arrives in fragments; must be assembled before calling the tool)
- Cache metrics tracked: `cache_creation_input_tokens`, `cache_read_input_tokens`

**Source files:** `services/api/streaming.py`, `services/api/client.py`, `types/message.py`

---

### Slide 13 · Retry & Token Budget

**Title:** Retry Strategy & Token Budgets

**Key content:**
- `stream_message_with_retry()` wraps the base streaming call
- Default `max_tokens`: 8,192
- On `stop_reason == "max_tokens"` (truncation): escalate to 64,000 and retry
- `CLAUDE_CODE_MAX_CONTEXT_TOKENS` env var overrides the context window ceiling
- Token usage tracked cumulatively across turns: input, output, cache creation, cache read
- `utils/tokens.py` (181 lines): heuristic token estimation for budget planning (without calling the API)
- Auto-compaction triggered when context approaches 80% / 95% of window

**Source files:** `services/api/streaming.py`, `utils/tokens.py`, `context/auto_compact.py`

---

## Section 6 — Tool System (Slides 14–16)

### Slide 14 · Tool Abstraction

**Title:** Tools: Abstract Base & Registry

**Key content:**
- `tools/base.py`: abstract `Tool(ABC)` with four key methods:
  ```python
  async def call(self, input_data: dict, context: ToolContext) -> ToolResult: ...
  def is_read_only(self) -> bool: ...
  def is_concurrency_safe(self, input_data: dict | None = None) -> bool: ...
  def is_enabled(self) -> bool: ...
  ```
- `ToolContext`: carries session state passed to every tool call (messages, abort event, permission callbacks, current session ID)
- `ToolResult`: output string + `is_error` flag
- `tools/registry.py`: two global lists — `_builtin_tools` and `_mcp_tools`
  - `get_all_tools()` filters by `is_enabled()`
  - `find_tool_by_name(name)` for lookup by Claude's tool name
  - `register_builtin_tools()` / `register_mcp_tools()`

**Source files:** `tools/base.py`, `tools/registry.py`, `types/tool.py`

---

### Slide 15 · Built-in Tools Catalog

**Title:** Built-in Tools: All 16

**Key content:**
| Tool | Read-Only | Concurrency-Safe | Notes |
|------|:---------:|:----------------:|-------|
| Read | Yes | Yes | Line-range aware |
| Glob | Yes | Yes | File pattern matching |
| Grep | Yes | Yes | Regex content search |
| Bash | Varies | Varies | Read-only when command is safe |
| Write | No | No | Create/overwrite files |
| Edit | No | No | Find-replace editing |
| Agent | Varies | Yes | Sub-agent delegation |
| Skill | No | No | Invoke a skill by name |
| TodoWrite | No | No | In-memory checklist |
| TaskCreate | No | No | Persistent task creation |
| TaskUpdate | No | No | Update status/metadata |
| TaskGet | No | No | Retrieve task by ID |
| TaskList | No | No | List all tasks |
| EnterPlanMode | No | No | Switch to read-only mode |
| ExitPlanMode | No | No | Restore full permissions |
| MemoryWrite | No | No | Persist project memory |

- Highlight: `AgentTool` can itself spawn recursive agentic loops
- Highlight: `SkillTool` injects skill system prompts mid-conversation

**Source files:** `tools/` (each `*_tool.py` file)

---

### Slide 16 · Permission System

**Title:** Permission System: Modes, Rules & Hierarchy

**Key content:**
- Three permission modes:
  - `default` — read-only tools auto-allowed; write/shell require inline confirmation
  - `plan` — only Read, Grep, Glob (and read-only Bash) allowed; all mutations blocked
  - `auto` — all operations auto-allowed (for scripting/CI)
- Rule syntax examples:
  - `"Read"` — exact tool name
  - `"Bash(npm test *)"` — parameterised with wildcard
  - `"mcp__filesystem*"` — wildcard MCP tool namespace
- `PermissionBehavior`: `"allow"` | `"ask"` | `"deny"`
- `PermissionDecision`: `"allow_once"` | `"allow_always"` | `"deny"`
- Load hierarchy (later overrides earlier): user settings → project settings → session rules (`allow_always`)
- Plan mode hard blocks: `PLAN_ALLOWED_TOOLS = {"Read", "Grep", "Glob"}`

**Source files:** `permissions/permissions.py` (300+ lines)

---

## Section 7 — Extensions & Integrations (Slides 17–20)

### Slide 17 · MCP Integration

**Title:** MCP: Model Context Protocol

**Key content:**
- What MCP is: a standard protocol for exposing tool APIs to LLMs; uses stdio, HTTP, or SSE transports
- Config lives in `~/.agent-butler/settings.json` under `mcpServers` key
- Bootstrap (`services/mcp/bootstrap.py`):
  1. Parse server configs (YAML/JSON)
  2. Connect with 30-second timeout
  3. Call `list_tools()` on each server
  4. Wrap results as native `Tool` objects with `mcp__<server>__<tool>` naming
  5. Register in `_mcp_tools` global
- Connection caching by config signature (avoids reconnection on every turn)
- Schema normalisation (`normalization.py`): adapts MCP JSON Schema to Pydantic-compatible form

**Source files:** `services/mcp/bootstrap.py`, `services/mcp/client.py`, `services/mcp/fetch_tools.py`, `services/mcp/normalization.py`

---

### Slide 18 · Skills System

**Title:** Skills: Reusable Markdown Workflows

**Key content:**
- A skill is a `.md` file with YAML frontmatter:
  ```markdown
  ---
  name: review
  description: Perform a thorough code review
  allowedTools: [Read, Grep, Glob]
  budget: 3000
  paths: [src/*, tests/*]
  ---
  You are reviewing code...
  ```
- Two activation modes:
  - **Dynamic** (no `paths`): always visible to the model
  - **Conditional** (has `paths`): activated only when user's CWD matches a path pattern
- `budget` field: token limit for skill context; `services/skills/budget.py` filters skills that exceed remaining budget
- Load order: user scope (`~/.agent-butler/skills/`) then project scope (`./.agent-butler/skills/`); project overrides user
- Invoked via `SkillTool` — injects skill system prompt into the current turn

**Source files:** `services/skills/registry.py`, `services/skills/load_skills_dir.py`, `services/skills/parse_frontmatter.py`, `services/skills/conditional.py`, `services/skills/budget.py`

---

### Slide 19 · Sub-Agents

**Title:** Sub-Agents: Delegation & Isolation

**Key content:**
- `agents/`: defines `AgentDefinition` (dataclass) + execution engines
- `AgentDefinition` key fields:
  - `agent_type`, `description`, `system_prompt`
  - `tools_allow` / `tools_deny` (tool whitelist/blacklist)
  - `isolation`: `"none"` | `"worktree"` (fresh git worktree for file mutations)
  - `max_turns`: cap on agentic loop iterations
  - `model`: optional model override
- **Foreground** (`run_agent.py`): blocks until done; result returned inline
- **Background** (`run_async_agent.py`): returns `agent_id` immediately; completion injected as notification in next user turn
- **Worktree isolation**: `utils/worktree.py` (129 lines) — creates isolated git worktree, passes parent context; auto-removed if unchanged
- Built-in agents: `explore` (Read/Grep/Glob only) and `general_purpose` (full access)

**Source files:** `agents/types.py`, `agents/run_agent.py`, `agents/run_async_agent.py`, `utils/worktree.py`, `agents/built_in/`

---

### Slide 20 · Extending the Platform

**Title:** How to Extend Agent Butler

**Key content:**
- **Add a custom tool:**
  1. Subclass `Tool` in `tools/`
  2. Implement `call()`, `is_read_only()`, `is_concurrency_safe()`, `is_enabled()`
  3. Call `register_builtin_tools([MyTool()])` in bootstrap
- **Add a skill:**
  1. Create `~/.agent-butler/skills/my-skill.md` with YAML frontmatter
  2. Optionally set `paths` for conditional activation
  3. No code change needed — auto-discovered at startup
- **Add a custom agent:**
  1. Create `~/.agent-butler/agents/my-agent.json` with `AgentDefinition` fields
  2. Reference via `agent_type` in `AgentTool` calls
- **Connect an MCP server:**
  1. Add entry to `mcpServers` in `~/.agent-butler/settings.json`
  2. Specify `command`, `args`, `transport` (`stdio` | `http` | `sse`)
  3. Restart; tools auto-appear with `mcp__<server>__` prefix

**Source files:** `tools/base.py`, `agents/registry.py`, `services/mcp/config.py`

---

## Section 8 — Platform Services (Slides 21–24)

### Slide 21 · Sandbox (macOS)

**Title:** Sandbox: macOS `sandbox-exec` Integration

**Key content:**
- macOS only (auto-detected via `sandbox/availability.py`; no-op on Linux/Windows)
- `sandbox/wrap.py`: compiles a Sandbox Profile Language (SBPL) profile and wraps commands:
  ```bash
  /usr/bin/sandbox-exec -p '<compiled-profile>' /bin/bash -lc '<command>'
  ```
- `sandbox/build_profile.py`: composes profile from four rule sets:
  - `allow_read` paths, `allow_write` paths, `deny_write` overrides, allowed network domains
- `sandbox/should_use.py`: per-command gate — excludes certain commands (e.g., interactive processes) from sandboxing
- `sandbox/split_command.py`: handles `&&` / `||` compound commands before wrapping
- `sandbox/violations.py`: detects and logs policy violations from stderr

**Source files:** `sandbox/wrap.py`, `sandbox/build_profile.py`, `sandbox/should_use.py`, `sandbox/types.py`

---

### Slide 22 · Terminal UI

**Title:** Terminal UI: Rich Live + UIEvents

**Key content:**
- `ui/app.py`: creates `SessionController`, runs async REPL, dispatches slash commands
- `ui/layout.py`: `TUILayout` — composes all panels; `StreamingBuffer` throttles Rich refreshes at ~30 ms
- `ui/session_hook.py` (395 lines): `SessionController` emits `UIEvent` objects — `UISpinnerStart`, `UITextDelta`, `UIToolStart`, `UIToolDone`, `UITurnComplete`, `UIError`, `UIPermissionRequest`
- UI components:
  - `ConversationView` — markdown-rendered message history
  - `ToolCard` — live tool invocation cards with input/output
  - `TodoListView` — session-level checklist
  - `TaskListView` — persistent task graph
  - `StatusBar` — model name, permission mode, cumulative token usage
  - `Spinner` — breathing-star + shimmer effect while streaming
- `ui/input_prompt.py`: `prompt_toolkit` input with persistent history

**Source files:** `ui/app.py`, `ui/layout.py`, `ui/session_hook.py`, `ui/events.py`, `ui/tool_card.py`, `ui/status_bar.py`

---

### Slide 23 · Context Management

**Title:** Context Management: System Prompt & Compaction

**Key content:**
- `context/system_prompt.py`: assembles system prompt dynamically each turn from:
  - Static core instructions (tool usage rules, workspace boundaries)
  - Git context: branch, status, recent commit (if git repo)
  - Environment: OS, CWD, current date
  - `AGENT.md`: user-provided context from `~/.agent-butler/AGENT.md`
  - Tool definitions: generated from registry
  - Skill descriptions: from skills registry
  - Agent descriptions: from agents registry
- Auto-compaction (`context/auto_compact.py`):
  - Monitors budget via `utils/tokens.py`
  - Warns at 80% of context window
  - Triggers summarisation at 95% (`context/compaction.py`)
- Memory system (`context/memory/`):
  - `memdir.py`: CRUD for persistent markdown memory files in `~/.agent-butler/projects/<cwd>/memory/`
  - `find_relevant.py`: semantic retrieval of relevant memories for current turn
  - Written by `MemoryWriteTool`

**Source files:** `context/system_prompt.py`, `context/auto_compact.py`, `context/compaction.py`, `context/memory/`

---

### Slide 24 · State & Persistence

**Title:** State & Persistence: Five Stores

**Key content:**
| Store | Location | Format | Scope |
|-------|----------|--------|-------|
| `task_store.py` | `~/.agent-butler/tasks/<list_id>/` | File-locked JSON (one file per task) | Cross-session, persistent |
| `session/storage.py` | `~/.agent-butler/projects/<cwd>/sessions/` | JSONL (one line per event) | Per-session, resumable |
| `todo_store.py` | In-memory only | List of `TodoItem` | Current session only |
| `notification_store.py` | In-memory queue | List of notification objects | Current session, background agents |
| `async_agent_store.py` | In-memory dict | `agent_id → AgentRunResult` | Current session, background agents |

- `filelock` used in `task_store.py` to prevent concurrent write corruption
- Sessions are resumable: `--resume SESSION_ID` replays JSONL history into `messages[]`
- Background agent completions are queued in `notification_store` and injected at the start of the next user turn

**Source files:** `state/task_store.py`, `session/storage.py`, `state/todo_store.py`, `state/notification_store.py`, `state/async_agent_store.py`

---

## Section 9 — Testing & Development (Slides 25–26)

### Slide 25 · Test Suite

**Title:** Testing: Structure & Coverage

**Key content:**
- `tests/conftest.py`: shared fixtures (mock tool context, temporary directories, fake API responses)
- Five test modules:

| Module | What it covers |
|--------|---------------|
| `test_tools.py` | Tool registry operations, tool execution contracts, read-only flags |
| `test_streaming.py` | `StreamEvent` accumulation, partial JSON assembly for tool use blocks |
| `test_tasks.py` | `Task` and `TaskStatus` model serialisation, field validation |
| `test_permissions.py` | Rule matching (exact, wildcard, parameterised), mode transitions, plan mode restrictions |
| `test_sandbox.py` | SBPL profile compilation, compound command splitting, `should_use` gating |

- Run: `pytest tests/ -v`
- Note: integration tests (actual API calls, MCP connections) are not included — unit-level only

**Source files:** `tests/`

---

### Slide 26 · How to Extend

**Title:** Developer Guide: Extension Patterns

**Key content:**
- **Custom Tool checklist:**
  - [ ] Subclass `Tool(ABC)` in `tools/`
  - [ ] Implement `call()`, `is_read_only()`, `is_concurrency_safe()`, `is_enabled()`
  - [ ] Add to `register_builtin_tools([...])` in `cli.py` bootstrap
  - [ ] Tool name appears in system prompt automatically
- **Custom Skill checklist:**
  - [ ] Create `~/.agent-butler/skills/<name>.md`
  - [ ] Add YAML frontmatter: `name`, `description`, optional `allowedTools`, `budget`, `paths`
  - [ ] No code change; auto-discovered at startup
- **Custom Agent checklist:**
  - [ ] Create `~/.agent-butler/agents/<type>.json`
  - [ ] Specify `system_prompt`, `tools_allow`/`tools_deny`, `isolation`, `model`
  - [ ] Reference `agent_type` in `AgentTool` calls
- **MCP Server checklist:**
  - [ ] Add to `mcpServers` in `~/.agent-butler/settings.json`
  - [ ] Specify `command`, `args`, `transport` (`stdio` | `http` | `sse`)
  - [ ] Restart; tools auto-prefixed `mcp__<server>__<tool>`

**Source files:** `tools/base.py`, `agents/registry.py`, `services/mcp/config.py`, `cli.py`

---

## Section 10 — Wrap-up (Slides 27–28)

### Slide 27 · Design Patterns & Key Takeaways

**Title:** Design Patterns & Takeaways

**Key content:**
- **Async-first**: `asyncio` throughout — `asyncio.gather()` for concurrent tools, `aiofiles` for file I/O, async generators for streaming
- **Pydantic for everything**: all messages, tool results, tasks, skills, agents are `BaseModel` — validated at boundaries, serialisable to JSON
- **Layered separation of concerns**: each layer has one job; UI layer never calls API directly
- **Multi-source config hierarchy**: user → project → session — predictable override semantics
- **Everything is a tool/skill/agent**: extensibility without touching core code
- **Generator-based streaming**: the agentic loop, session controller, and API layer all communicate via `AsyncGenerator` — no shared mutable state between layers
- **Minimal blast radius**: `is_concurrency_safe()`, `is_read_only()`, permission modes, and sandbox profiles all limit the scope of any single operation

**Source files:** N/A (synthesis slide)

---

### Slide 28 · Q&A

**Title:** Questions?

**Key content:**
- Open Q&A
- Reference links:
  - `python/README.md` — full usage documentation
  - `python/agent_butler/` — source code
  - `python/tests/` — test suite
- Invitation to contribute: custom tools, skills, MCP servers

**Source files:** `README.md`
