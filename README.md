# Agent Butler — Python

A terminal-native coding assistant recreating the Claude Code experience with an integrated workspace **Harness Engineering** system. Beyond simple tool execution, Agent Butler transforms your repository into the single source of truth for agent behavior—enforcing WIP=1 focus limits, performing zero-trust verification test checks on exit, and maintaining strict session continuity across context compactions through structured markdown templates.

![Agent Butler Logo](images/logo.png)

## Architecture

The Python version mirrors the TypeScript five-layer architecture:

```text
+---------------------------------------------------+
| 1. Interaction Layer                              |
|    Rich console, prompt_toolkit input, Live       |
+---------------------------------------------------+
| 2. Orchestration Layer                            |
|    SessionController, multi-turn flow, commands   |
+---------------------------------------------------+
| 3. Core Agentic Loop                              |
|    Reason -> tool call -> observe -> continue     |
+---------------------------------------------------+
| 4. Tooling Layer                                  |
|    File, shell, search, agent delegation          |
+---------------------------------------------------+
| 5. Model Communication Layer                      |
|    Anthropic SDK streaming, retry, accumulation   |
+---------------------------------------------------+
```

## Requirements

- **Python >= 3.11**
- **Anthropic API key** (`ANTHROPIC_AUTH_TOKEN` environment variable)
- **macOS** (optional, for sandbox-exec support; sandbox is automatically disabled on Linux/Windows)

## Installation

```bash
cd python

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
cd python
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Environment Variables

| Variable                           | Description                                                | Default                      |
| ---------------------------------- | ---------------------------------------------------------- | ---------------------------- |
| `ANTHROPIC_AUTH_TOKEN`           | Anthropic API key                                          | (required)                   |
| `ANTHROPIC_MODEL`                | Default model name                                         | `claude-sonnet-4-20250514` |
| `ANTHROPIC_BASE_URL`             | Custom API base URL                                        | Anthropic default            |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | Override context window size                               | model default                |
| `AGENT_BUTLER_DEBUG`             | Enable debug logging to stderr                             | `0`                        |
| `AGENT_BUTLER_DEBUG_STREAM`      | Log raw SSE events to `~/.agent-butler/stream-debug.log` | `0`                        |

Environment variables can also be set in:

1. `~/.claude.json` (global config, `env` field)
2. `~/.claude/settings.json` (user settings, `env` field)
3. `.env` in the working directory (project-local, highest priority)

## Usage

### Interactive Mode

```bash
# Start with default model
agent-butler

# Specify a model
agent-butler --model claude-opus-4-20250514

# Start in plan mode (read-only tools only)
agent-butler --plan

# Start in auto mode (no permission prompts)
agent-butler --auto

# Resume a previous session
agent-butler --resume SESSION_ID

# Change working directory
agent-butler --cwd /path/to/project
```

### Interactive Commands

Once inside a session, the following slash commands are available:

| Command                      | Description                                                                                               |
| ---------------------------- | --------------------------------------------------------------------------------------------------------- |
| `/help`                    | Show all available commands with descriptions                                                             |
| `/clear`                   | Wipe the conversation history and start fresh                                                             |
| `/cost`                    | Display token usage for the current session (input / output totals)                                       |
| `/model`                   | Show the currently active model name                                                                      |
| `/model <name>`            | Switch to a different model for the remainder of the session (e.g.`/model claude-opus-4-20250514`)      |
| `/mode`                    | Show the current permission mode (`default`, `plan`, or `auto`)                                     |
| `/mode <mode>`             | Switch permission mode —`default` (confirm writes), `plan` (read-only), or `auto` (no prompts)     |
| `/tasks`                   | Show the current task system mode (`task`, `todo`, or `off`)                                        |
| `/tasks <mode>`            | Switch the task system —`task` (persistent task graph), `todo` (session-level checklist), or `off` |
| `/compact`                 | Trigger conversation compaction to free context window space                                              |
| `/skills`                  | List all loaded skills (user-scope and project-scope) with descriptions                                   |
| `/agents`                  | List all registered sub-agent definitions (built-in + custom)                                             |
| `/mcp`                     | Show connected MCP servers and their available tools                                                      |
| `/exit` `/quit` `/bye` | Exit the session                                                                                          |

### Permission Prompts

When the agent attempts a write or shell operation in `default` (or `plan`) mode, an inline permission prompt appears:

```
⚠ Permission required: Bash
  args: command=npm test
  risk: Medium risk: shell command may change files or git state
  always allow rule: Bash(npm *)
  [y] allow once   [n] deny   [a] always allow (session)
```

| Key   | Action                                                                                       |
| ----- | -------------------------------------------------------------------------------------------- |
| `y` | Allow this single operation                                                                  |
| `n` | Deny the operation (the agent sees "Permission denied")                                      |
| `a` | Allow this operation**and** auto-allow matching operations for the rest of the session |

In `--auto` mode, all permission prompts are skipped and every operation is auto-allowed.

### Keyboard Shortcuts

| Key              | Action                                                                               |
| ---------------- | ------------------------------------------------------------------------------------ |
| `Ctrl+C`       | Interrupt the currently running agent turn (stops streaming, cancels tool execution) |
| `Ctrl+D`       | Exit the session (same as `/exit`)                                                 |
| Up / Down arrows | Navigate command history in the input prompt                                         |

### Live TUI Elements

During an active agent turn, the terminal displays real-time updates:

| Element                     | Description                                                                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Streaming text**    | Assistant response text appears character-by-character as the model generates it                                                                   |
| **Tool call cards**   | Each tool invocation shows `⚡ Using tool: <name>` while running, then `✓ <name> (<N> chars)` on success or `✗ <name> — error` on failure |
| **Spinner**           | A breathing-star animation with shimmer effect displays during model thinking, permission waits, and tool execution                                |
| **Todo list**         | Session-level checklist rendered as `[ ]` (pending), `[~]` (in progress), `[x]` (completed)                                                  |
| **Task graph**        | Persistent task list showing `#<id> [<status>] <subject>` with blocking relationships                                                            |
| **Permission dialog** | Yellow-bordered inline prompt with tool name, args summary, risk level, and allow/deny options                                                     |
| **Status bar**        | Shows current model, permission mode, token usage totals, and context window percentage                                                            |
| **System notices**    | Info (dim) or error (red) messages for command results, compaction events, and errors                                                              |

### Print Mode (Non-Interactive)

```bash
# Single-shot query, prints response and exits
agent-butler --print "Explain the main function in src/main.py"

# Pipe input
echo "What does this code do?" | agent-butler --print
```

In print mode, the agent's response streams directly to stdout without the TUI. Permission prompts are handled via stdin input. Token usage is printed to stderr after the response.

## Built-in Tools

The agent ships with 16 built-in tools:

| Tool              | Description                                               | Concurrency Safe |
| ----------------- | --------------------------------------------------------- | :--------------: |
| `Read`          | Read file contents with optional line range               |       Yes       |
| `Write`         | Create or overwrite files                                 |        No        |
| `Edit`          | Find-and-replace unique strings in files                  |        No        |
| `Glob`          | Find files by glob pattern                                |       Yes       |
| `Grep`          | Search file contents by regex (uses ripgrep if available) |       Yes       |
| `Bash`          | Execute shell commands                                    |        No        |
| `Agent`         | Delegate tasks to sub-agents                              |       Yes       |
| `Skill`         | Execute named skills from the registry                    |        No        |
| `TodoWrite`     | Update the session-level todo list                        |        No        |
| `TaskCreate`    | Create a persistent task                                  |        No        |
| `TaskUpdate`    | Update a persistent task                                  |        No        |
| `TaskGet`       | Retrieve a task by ID                                     |        No        |
| `TaskList`      | List all tasks                                            |        No        |
| `EnterPlanMode` | Switch to plan mode                                       |        No        |
| `ExitPlanMode`  | Exit plan mode and restore full access                    |        No        |
| `MemoryWrite`   | Save durable project memory                               |        No        |

Concurrency-safe tools (Read, Grep, Glob, Agent) are automatically batched and run in parallel via `asyncio.gather()`.

## Key Features

### Streaming

The streaming module wraps the Anthropic SDK's streaming API with:

- Per-index JSON accumulation for overlapping `tool_use` blocks
- Automatic escalated retry on `max_tokens` truncation (8K → 64K)
- Debug logging of raw SSE events (opt-in via `AGENT_BUTLER_DEBUG_STREAM`)

### Permission System

Three permission modes:

- **default** — read-only tools auto-allowed; write/shell tools require confirmation
- **plan** — only Read, Grep, Glob, and read-only Bash allowed
- **auto** — all operations auto-allowed (no prompts)

Permissions are configured via `~/.agent-butler/settings.json` (user) and `<cwd>/.agent-butler/settings.json` (project). Project settings override user settings.

```json
{
  "allow": ["Bash(npm test *)", "Bash(git status)", "Read", "Glob"],
  "deny": ["Bash(rm *)", "Bash(sudo *)"],
  "mode": "default"
}
```

### Sandbox (macOS)

On macOS, Bash commands can run inside a `sandbox-exec` profile that restricts filesystem writes and network access. The sandbox is automatically disabled on non-macOS platforms.

Configure in settings.json:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["docker *", "npm install"],
    "filesystem": {
      "allowWrite": ["~/projects"],
      "denyWrite": ["/etc"]
    }
  }
}
```

### Sub-Agents

The `Agent` tool spawns isolated sub-agents with their own context windows:

- **Foreground** — blocks until the sub-agent completes, returns a structured result
- **Background** — returns immediately with an `agent_id`; the sub-agent runs asynchronously and a `<task-notification>` is injected when it finishes

Sub-agents support **worktree isolation** — a fresh `git worktree` is created so the sub-agent's file edits don't touch the main working copy.

### MCP (Model Context Protocol)

Connect to MCP servers via three transport types:

- **stdio** — local subprocess (e.g., `npx -y @modelcontextprotocol/server-filesystem`)
- **http** — Streamable HTTP (recommended for remote servers)
- **sse** — legacy SSE-only servers

Configure in `~/.agent-butler/settings.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "remote-api": {
      "type": "http",
      "url": "https://mcp.example.com",
      "headers": { "Authorization": "Bearer token" }
    }
  }
}
```

### Skills

Skills are Markdown files with YAML frontmatter that define reusable workflows. They are loaded from:

1. `~/.agent-butler/skills/` (user-level)
2. `<cwd>/.agent-butler/skills/` (project-level, overrides user)

```markdown
---
name: review
description: Perform a thorough code review
allowedTools: [Read, Grep, Glob]
---

You are reviewing code. Follow these steps:
1. Read the changed files
2. Check for bugs and style issues
3. Provide structured feedback
```

Invoke via the `Skill` tool or type `/review` in the interactive prompt.

### Context Management

- **System prompt** — assembled from git context, AGENT.md, tool definitions, skills, and agents
- **Auto-compaction** — automatically summarizes older messages when approaching the context window limit
- **Token budget** — monitors estimated tokens vs. context window, with warning/blocking thresholds
- **Project memory** — persistent markdown files in `~/.agent-butler/projects/<cwd>/memory/`

### Session Persistence

Sessions are stored as JSONL files in `~/.agent-butler/projects/` and can be resumed with `--resume`. Tasks persist across restarts in `~/.agent-butler/tasks/`.

### Harness-Managed Workspaces & Templates

Agent Butler dynamically detects if it is operating inside a **Harness-Managed Workspace** by checking for key files (`feature_list.json`, `CLAUDE.md`, or `AGENTS.md`) in the working directory or its parent folders. 

When **Harness Mode** is active, Agent Butler switches to repository-tracked governance:
- **Redirection**: Task management tools (`TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList`) bypass the global task database and read/write directly to the project's local `feature_list.json` file in-place.
- **WIP=1 Constraint**: Enforces that only one feature can be in the `in_progress` status at a time, preventing split-focus or drive-by refactoring.
- **Prompt Injection**: Dynamically injects project rules (`CLAUDE.md` / `AGENTS.md`), progress logs (`claude-progress.md` / `PROGRESS.md`), and decisions logs (`decisions.md`) directly into the system prompt.
- **Exit Gates**: If a feature is marked `passing` during the turn, Agent Butler intercepts loop completion and executes the project's verification test suite. If tests fail, the exit is aborted and the failure details are fed back to the agent to be fixed.

#### Using Workspace Templates
A set of pre-configured templates is available in the root `templates/` directory of the Agent Butler repository. Copy these templates directly into the **root of your target project** to set up a Harness-Managed Workspace.

##### 1. Core Templates (Get Started First)
Copy these four files into your project root first:
- **`CLAUDE.md` (or `AGENTS.md`)**: The root instruction and rules configuration. Adjust the startup workflow steps and command mappings (Tests, Lint, Type Check, Full verify) to match your stack.
- **`init.sh`**: The startup and verification script. Edit the install, verify, and start commands at the top. Make it executable (`chmod +x init.sh`).
- **`claude-progress.md`**: The progress log. Serves as the session-to-session state-tracking log for the agent.
- **`feature_list.json`**: The machine-readable feature database. Edit it to list your project features, along with their `verification_command` and human-readable verification steps.

##### 2. Advanced/Situational Templates (Add as your project grows)
- **`READY.md`**: The startup readiness checklist. If `READY.md` is missing from the workspace root on startup, Agent Butler triggers the **Initialization Phase Gate**, forcing the agent to verify the baseline test suite, compile readiness rules, and commit a clean baseline before allowing any feature work.
- **`decisions.md`**: An architectural decisions log to keep track of active constraints and rejected alternatives.
- **`CONSTRAINTS.md` & `check_boundaries.py`**: Defensively enforces architectural invariants (e.g. forward-only import flows across layers).
- **`clean-state-checklist.md`**: A list of checks the agent and developer run through at the end of each session (e.g., verifying builds/tests pass and removing debug logs/temp files).
- **`session-handoff.md`**: A template to write a compact context handoff note for the next session.
- **`evaluator-rubric.md`**: A rubric to score the output quality of the agent's completed work.
- **`quality-document.md`**: Grades the verification and health status of product domains and architectural layers over time.

## Project Structure

```text
python/
├── pyproject.toml                          # Package metadata and dependencies
├── agent_butler/
│   ├── __init__.py
│   ├── __main__.py                         # python -m agent_butler
│   ├── cli.py                              # CLI arg parsing and bootstrap
│   │
│   ├── types/                              # Pydantic models
│   │   ├── message.py                      # ContentBlock, Usage, StreamEvent
│   │   ├── tool.py                         # ToolContext, ToolResult
│   │   ├── task.py                         # Task, TaskStatus
│   │   ├── todo.py                         # TodoItem, TodoStatus
│   │   ├── skill.py                        # Skill, SkillFrontmatter
│   │   └── mcp.py                          # McpServerConfig, McpServerConnection
│   │
│   ├── utils/                              # Utilities
│   │   ├── paths.py                        # ~/.agent-butler/ path resolution
│   │   ├── tokens.py                       # Token estimation heuristics
│   │   ├── settings.py                     # JSON settings file reader
│   │   ├── load_env.py                     # Multi-source .env loading
│   │   ├── log.py                          # Debug/warn logging
│   │   ├── stream_debug.py                 # SSE event logging
│   │   ├── task_output.py                  # Sub-agent output file helpers
│   │   └── worktree.py                     # Git worktree management
│   │
│   ├── constants/
│   │   └── spinner_verbs.py                # Loading spinner text
│   │
│   ├── services/
│   │   ├── api/
│   │   │   ├── client.py                   # Anthropic client singleton
│   │   │   └── streaming.py                # Streaming + retry + accumulation
│   │   ├── mcp/
│   │   │   ├── client.py                   # MCP server connections
│   │   │   ├── registry.py                 # MCP server registry
│   │   │   ├── bootstrap.py                # MCP startup
│   │   │   ├── config.py                   # MCP config parsing
│   │   │   ├── fetch_tools.py              # MCP tool discovery
│   │   │   ├── normalization.py            # MCP data normalization
│   │   │   └── string_utils.py             # MCP naming helpers
│   │   └── skills/
│   │       ├── registry.py                 # Skills registry
│   │       ├── load_skills_dir.py          # SKILL.md disk scanner
│   │       ├── bootstrap.py                # Skills startup
│   │       ├── budget.py                   # Budget-aware skill listing
│   │       ├── conditional.py              # Conditional activation
│   │       └── parse_frontmatter.py        # YAML frontmatter parser
│   │
│   ├── tools/
│   │   ├── base.py                         # Tool ABC + helpers
│   │   ├── registry.py                     # Tool registration and lookup
│   │   ├── path_utils.py                   # Path resolution for tools
│   │   ├── bash_tool.py                    # Shell command execution
│   │   ├── file_read_tool.py               # File reading
│   │   ├── file_write_tool.py              # File writing
│   │   ├── file_edit_tool.py               # String-replace editing
│   │   ├── glob_tool.py                    # Glob file search
│   │   ├── grep_tool.py                    # Regex content search
│   │   ├── agent_tool.py                   # Sub-agent delegation
│   │   ├── skill_tool.py                   # Skill invocation
│   │   ├── todo_write_tool.py              # Todo list management
│   │   ├── task_create_tool.py             # Persistent task creation
│   │   ├── task_update_tool.py             # Persistent task updates
│   │   ├── task_get_tool.py                # Task retrieval
│   │   ├── task_list_tool.py               # Task listing
│   │   ├── enter_plan_mode_tool.py         # Plan mode entry
│   │   ├── exit_plan_mode_tool.py          # Plan mode exit
│   │   └── memory_write_tool.py            # Project memory writes
│   │
│   ├── sandbox/
│   │   ├── types.py                        # Sandbox type definitions
│   │   ├── settings.py                     # Sandbox settings loading
│   │   ├── availability.py                 # Platform detection
│   │   ├── should_use.py                   # Per-command sandbox gate
│   │   ├── split_command.py                # Compound command splitter
│   │   ├── build_profile.py                # Profile composition
│   │   ├── macos_profile.py (wrap.py)      # SBPL compiler + wrapping
│   │   └── violations.py                   # Violation detection
│   │
│   ├── permissions/
│   │   └── permissions.py                  # Full permission engine
│   │
│   ├── core/
│   │   ├── agentic_loop.py                 # Reason→Act→Observe loop
│   │   └── query_engine.py                 # QueryEngine orchestration
│   │
│   ├── context/
│   │   ├── system_prompt.py                # System prompt assembly
│   │   ├── compaction.py                   # Conversation summarization
│   │   ├── auto_compact.py                 # Token budget triggers
│   │   ├── plans.py                        # Plan file management
│   │   ├── plan_attachments.py             # Plan attachment handling
│   │   ├── claude_md.py                    # AGENT.md loading
│   │   └── memory/
│   │       ├── memdir.py                   # Memory directory CRUD
│   │       ├── memory_types.py             # Memory type definitions
│   │       └── find_relevant.py            # Memory retrieval
│   │
│   ├── agents/
│   │   ├── types.py                        # AgentDefinition, AgentRunResult
│   │   ├── registry.py                     # Agent registration
│   │   ├── bootstrap.py                    # Agent startup
│   │   ├── run_agent.py                    # Foreground agent execution
│   │   ├── run_async_agent.py              # Background agent lifecycle
│   │   ├── load_agents_dir.py              # Agent disk loader
│   │   ├── prompt_injection.py             # Prompt augmentation
│   │   ├── resolve_tools.py                # Tool filtering for agents
│   │   └── built_in/
│   │       ├── explore.py                  # Read-only exploration agent
│   │       └── general_purpose.py          # Full-access agent
│   │
│   ├── session/
│   │   ├── storage.py                      # JSONL session persistence
│   │   └── history.py                      # Conversation history helpers
│   │
│   ├── state/
│   │   ├── task_store.py                   # Disk-backed task CRUD
│   │   ├── async_agent_store.py            # Background agent state
│   │   ├── sub_agent_progress.py           # Sub-agent progress tracking
│   │   ├── notification_store.py           # Notification queue
│   │   ├── task_mode_store.py              # Task/todo mode toggle
│   │   └── todo_store.py                   # In-memory todo state
│   │
│   └── ui/
│       ├── app.py                          # Rich Live TUI controller
│       ├── events.py                       # UIEvent protocol (UITextDelta, UIToolStart, …)
│       ├── layout.py                       # TUILayout + StreamingBuffer (30ms throttle)
│       ├── session_hook.py                 # SessionController (async generator)
│       ├── conversation_view.py            # Markdown-rendered conversation history
│       ├── tool_card.py                    # Tool call card rendering
│       ├── todo_list_view.py               # Todo checklist rendering
│       ├── task_list_view.py               # Task graph rendering
│       ├── command_suggestions.py          # Slash command autocomplete
│       ├── status_bar.py                   # Model/mode/usage/permission bar
│       ├── spinner.py                      # Breathing-star + shimmer animation
│       └── input_prompt.py                 # prompt_toolkit input with history
│
└── tests/
    ├── conftest.py                         # Shared fixtures
    ├── test_tools.py                       # Tool registry tests
    ├── test_streaming.py                   # Stream event tests
    ├── test_tasks.py                       # Task model tests
    ├── test_permissions.py                 # Permission engine tests
    └── test_sandbox.py                     # Sandbox utility tests
```

## Development

### Running Tests

```bash
cd python
pytest tests/ -v
```

### Linting

```bash
ruff check agent_butler/
ruff format agent_butler/
```

### Type Checking

```bash
mypy agent_butler/
```

## On-disk Layout

Agent Butler stores state in `~/.agent-butler/`:

```text
~/.agent-butler/
├── settings.json                           # User-scope settings (permissions, MCP, sandbox)
├── AGENT.md                                # User-scope memory loaded into system prompt
├── tasks/                                  # Persistent task graphs (JSON, file-locked)
├── plans/                                  # Plan-mode plan files
├── projects/                               # Per-cwd memory + session transcripts
│   └── <encoded-cwd>/
│       ├── sessions/                       # JSONL session transcripts
│       ├── memory/                         # Project memory files
│       └── tasks/                          # Sub-agent output files
├── skills/                                 # User-scope skills (SKILL.md files)
├── agents/                                 # Custom agent definitions (JSON)
├── worktrees/                              # Git worktrees for isolated sub-agents
└── stream-debug.log                        # Opt-in raw SSE log
```

Per-project settings live in `<cwd>/.agent-butler/settings.json` and override user-scope settings.

## Caveats

**AGENT BUTLER project is:**
- An open-source recreation project
- A systems-engineering effort
- A long-term implementation of a local coding agent
- A public codebase evolving toward a full Claude Code-class CLI

**AGENT BUTLER is not:**
- A one-file demo
- A prompt-only wrapper around an API
- A finished product today
- A public mirror of any private course material

## License

MIT
