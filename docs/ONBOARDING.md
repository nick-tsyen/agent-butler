# Onboarding Guide: easy-agent

## Project Overview

| Field | Value |
|-------|-------|
| **Name** | easy-agent |
| **Description** | A terminal-native agentic coding system that recreates the Claude Code experience in open-source TypeScript/Node.js |
| **Languages** | TypeScript, TSX |
| **Frameworks** | React, Ink, Anthropic SDK, Model Context Protocol SDK |

## Architecture Layers

The system is organized into 6 layers, from user-facing UI down to external services.

### 1. Interaction Layer
Terminal UI, input handling, rendering. React/Ink-based terminal interface components.

**Key files:** `App.tsx`, `ConversationView.tsx`, `InputPrompt.tsx`, `MessageList.tsx`

### 2. Orchestration Layer
Multi-turn session flow, agent management, context engineering, state management.

**Key files:** `runAgent.ts`, `registry.ts`, `systemPrompt.ts`, `compaction.ts`, `taskStore.ts`

### 3. Core Agentic Loop
Reason → tool call → observe → continue. The autonomous execution engine.

**Key files:** `agenticLoop.ts`, `queryEngine.ts`

### 4. Tooling Layer
Local tools (file, shell, search), permission controls, sandboxing.

**Key files:** `Tool.ts`, `bashTool.ts`, `fileEditTool.ts`, `permissions.ts`, `wrapWithSandbox.ts`

### 5. Model Communication Layer
Streaming API communication with LLMs, MCP protocol, skills, utilities.

**Key files:** `client.ts`, `streaming.ts`, `mcp/client.ts`, `skills/registry.ts`

### 6. Scripts and Tests
Test scripts, smoke tests, and development utilities.

**Key files:** `test-agents.ts`, `test-tools.ts`, `test-mcp.ts`

## Key Concepts

- **Agentic Loop Pattern**: The core `agenticLoop.ts` implements a Reason→Act→Observe loop. It sends queries to the LLM, executes returned tool calls, feeds results back, and repeats until the task is complete.
- **Tool Interface**: All tools implement a common interface defined in `Tool.ts`. Each tool declares its own permissions and parameters.
- **Context Engineering**: The system carefully manages what the LLM sees via system prompts (`systemPrompt.ts`), conversation compaction (`compaction.ts`), plans (`plans.ts`), and persistent memory (`memdir.ts`).
- **Agent Registry**: Agents are registered and resolved through a registry pattern (`registry.ts`). Built-in agents (explore, generalPurpose) are defined in `agents/builtIn/`.
- **Sandboxing**: Bash commands can be sandboxed via macOS sandbox profiles (`macosProfile.ts`, `buildProfile.ts`) for safety.
- **MCP Integration**: External tool servers are discovered via the Model Context Protocol (`mcp/client.ts`, `mcp/registry.ts`).
- **Skills System**: Reusable prompt templates loaded from disk with frontmatter parsing and budget management.
- **State Stores**: Reactive state is managed via store modules (`taskStore.ts`, `asyncAgentStore.ts`, `todoStore.ts`) rather than a single global state.
- **Session Persistence**: Conversation history and session data are persisted via `session/storage.ts` and `session/history.ts`.

## Guided Tour

Follow these steps in order to understand the codebase from the ground up.

### Step 1: Project Overview — Entry Point
**File:** `src/entrypoint/cli.ts`

Start here. Understand how the CLI boots, parses arguments, and launches the application.

### Step 2: Type System
**Files:** `src/types/types.ts`, `src/types/tool.ts`, `src/types/message.ts`, `src/types/config.ts`, `src/types/task.ts`

The type definitions form the foundation. These shared types are used across all layers.

### Step 3: Model Communication
**Files:** `src/services/api/client.ts`, `src/services/api/streaming.ts`

The API client and streaming layer handle communication with the Anthropic LLM. This is the lowest layer — all LLM interaction flows through here.

### Step 4: Tool System
**Files:** `src/tools/Tool.ts`, `src/tools/index.ts`, `src/tools/bashTool.ts`, `src/tools/fileReadTool.ts`, `src/tools/fileWriteTool.ts`, `src/tools/fileEditTool.ts`

Tools are the agent's capabilities — file operations, bash execution, search, and more. Each tool implements a common interface and declares its own permissions.

### Step 5: Core Agentic Loop
**Files:** `src/core/agenticLoop.ts`, `src/core/queryEngine.ts`

The agentic loop is the heart of the system: send a query to the LLM, execute tool calls, observe results, and continue until done.

### Step 6: Context Management
**Files:** `src/context/systemPrompt.ts`, `src/context/compaction.ts`, `src/context/plans.ts`, `src/context/memory/memdir.ts`

Context engineering shapes what the LLM sees — system prompts, memory, plans, and compaction keep the conversation focused and within token limits.

### Step 7: Agent System
**Files:** `src/agents/types.ts`, `src/agents/registry.ts`, `src/agents/bootstrap.ts`, `src/agents/runAgent.ts`

Agents are higher-level orchestrators that can run sub-agents, manage tools, and inject prompts. The registry and bootstrap system initializes them.

### Step 8: Terminal UI
**Files:** `src/ui/App.tsx`, `src/ui/components/ConversationView.tsx`, `src/ui/components/InputPrompt.tsx`, `src/ui/components/MessageList.tsx`

The React/Ink terminal interface renders the conversation, tool calls, and status.

### Step 9: Sandbox & Permissions
**Files:** `src/sandbox/index.ts`, `src/sandbox/wrapWithSandbox.ts`, `src/permissions/permissions.ts`

Safety boundaries: sandboxing restricts bash execution, and the permission system controls which tools can be used and when user approval is needed.

### Step 10: Services: MCP & Skills
**Files:** `src/services/mcp/client.ts`, `src/services/mcp/registry.ts`, `src/services/skills/registry.ts`, `src/services/skills/loadSkillsDir.ts`

The MCP client enables tool discovery from external servers. Skills are reusable prompt templates loaded from disk.

## File Map

### Interaction Layer (`src/ui/`)
| File | Description | Complexity |
|------|-------------|------------|
| `App.tsx` | Root React/Ink application component | simple |
| `components/ConversationView.tsx` | Renders the full conversation with tool calls and messages | **complex** |
| `components/InputPrompt.tsx` | User text input component | simple |
| `components/MessageList.tsx` | Renders message history | moderate |
| `components/ModeSelector.tsx` | Mode switching UI | simple |
| `components/PlanApprovalDialog.tsx` | Dialog for plan approval flow | simple |
| `components/StatusBar.tsx` | Bottom status bar | simple |
| `components/TaskList.tsx` | Displays task list | moderate |
| `components/TodoList.tsx` | Displays todo items | moderate |
| `components/SubAgentCard.tsx` | Card for sub-agent status | moderate |
| `components/BackgroundAgentBar.tsx` | Background agent indicator | moderate |
| `components/Spinner.tsx` | Loading spinner | moderate |
| `components/ToolCallList.tsx` | Renders tool call results | simple |
| `components/CommandSuggestions.tsx` | Command autocomplete | simple |
| `components/SystemPanel.tsx` | System info panel | simple |
| `hooks/useAgentSession.ts` | Main session orchestration hook | **complex** |
| `hooks/usePromptInput.ts` | Input handling hook | moderate |
| `types.ts` | UI type definitions | simple |
| `utils/toolCardFormat.ts` | Tool card display formatting | moderate |

### Orchestration Layer (`src/agents/`, `src/context/`, `src/session/`, `src/state/`)
| File | Description | Complexity |
|------|-------------|------------|
| `agents/bootstrap.ts` | Agent bootstrap/initialization | simple |
| `agents/registry.ts` | Agent registration and lookup | moderate |
| `agents/runAgent.ts` | Agent execution entry point | moderate |
| `agents/runAsyncAgent.ts` | Async agent execution | moderate |
| `agents/loadAgentsDir.ts` | Loads agents from disk | **complex** |
| `agents/promptInjection.ts` | Injects prompts into agent context | moderate |
| `agents/resolveAgentTools.ts` | Resolves tools available to an agent | simple |
| `agents/builtIn/explore.ts` | Built-in explore agent definition | simple |
| `agents/builtIn/generalPurpose.ts` | Built-in general-purpose agent definition | simple |
| `agents/builtIn/index.ts` | Built-in agents barrel export | simple |
| `agents/types.ts` | Agent type definitions | simple |
| `context/systemPrompt.ts` | System prompt assembly | **complex** |
| `context/compaction.ts` | Conversation compaction/summarization | **complex** |
| `context/autoCompact.ts` | Auto-compaction triggers | **complex** |
| `context/plans.ts` | Plan creation and management | **complex** |
| `context/planAttachments.ts` | Plan attachment handling | **complex** |
| `context/claudeMd.ts` | CLAUDE.md file parsing | moderate |
| `context/memory/memdir.ts` | Memory directory management | **complex** |
| `context/memory/memoryTypes.ts` | Memory type definitions | moderate |
| `context/memory/findRelevantMemories.ts` | Memory retrieval | simple |
| `session/storage.ts` | Session persistence | **complex** |
| `session/history.ts` | Conversation history helpers | simple |
| `state/taskStore.ts` | Task state management | **complex** |
| `state/asyncAgentStore.ts` | Async agent state | **complex** |
| `state/subAgentProgressStore.ts` | Sub-agent progress tracking | **complex** |
| `state/notificationStore.ts` | Notification state | **complex** |
| `state/taskModeStore.ts` | Task mode state | moderate |
| `state/todoStore.ts` | Todo state management | moderate |

### Core Agentic Loop (`src/core/`)
| File | Description | Complexity |
|------|-------------|------------|
| `agenticLoop.ts` | The main Reason→Act→Observe loop (612 lines) | **complex** |
| `queryEngine.ts` | Query engine class for LLM communication (933 lines) | **complex** |

### Tooling Layer (`src/tools/`, `src/sandbox/`, `src/permissions/`)
| File | Description | Complexity |
|------|-------------|------------|
| `tools/Tool.ts` | Base tool interface and registration | moderate |
| `tools/index.ts` | Tool registry and exports | moderate |
| `tools/agentTool.ts` | Agent delegation tool (626 lines) | **complex** |
| `tools/bashTool.ts` | Shell command execution tool | moderate |
| `tools/fileReadTool.ts` | File reading tool | simple |
| `tools/fileWriteTool.ts` | File writing tool | simple |
| `tools/fileEditTool.ts` | File editing tool | moderate |
| `tools/globTool.ts` | File glob search tool | simple |
| `tools/grepTool.ts` | Content grep search tool | simple |
| `tools/skillTool.ts` | Skill loading tool | moderate |
| `tools/taskCreateTool.ts` | Task creation tool | simple |
| `tools/taskGetTool.ts` | Task retrieval tool | simple |
| `tools/taskListTool.ts` | Task listing tool | simple |
| `tools/taskUpdateTool.ts` | Task update tool | moderate |
| `tools/todoWriteTool.ts` | Todo write tool | moderate |
| `tools/enterPlanModeTool.ts` | Enter plan mode tool | simple |
| `tools/exitPlanModeTool.ts` | Exit plan mode tool | simple |
| `tools/memoryWriteTool.ts` | Memory write tool | simple |
| `tools/pathUtils.ts` | Path utility functions | moderate |
| `sandbox/index.ts` | Sandbox barrel exports | simple |
| `sandbox/wrapWithSandbox.ts` | Wraps commands with sandbox | simple |
| `sandbox/buildProfile.ts` | Builds sandbox profiles | **complex** |
| `sandbox/macosProfile.ts` | macOS-specific sandbox profile | moderate |
| `sandbox/settings.ts` | Sandbox settings management | **complex** |
| `sandbox/shouldUseSandbox.ts` | Sandbox availability check | moderate |
| `sandbox/availability.ts` | Sandbox availability detection | moderate |
| `sandbox/splitCommand.ts` | Command splitting utility | simple |
| `sandbox/violations.ts` | Sandbox violation handling | moderate |
| `sandbox/types.ts` | Sandbox type definitions | simple |
| `permissions/permissions.ts` | Permission system (444 lines) | **complex** |

### Model Communication Layer (`src/services/`, `src/types/`, `src/utils/`)
| File | Description | Complexity |
|------|-------------|------------|
| `services/api/client.ts` | Anthropic API client | moderate |
| `services/api/streaming.ts` | LLM streaming handler (400 lines) | moderate |
| `services/mcp/client.ts` | MCP client (445 lines) | **complex** |
| `services/mcp/registry.ts` | MCP server registry | moderate |
| `services/mcp/bootstrap.ts` | MCP bootstrap | moderate |
| `services/mcp/config.ts` | MCP configuration | moderate |
| `services/mcp/fetchTools.ts` | MCP tool fetching | moderate |
| `services/mcp/normalization.ts` | MCP data normalization | simple |
| `services/mcp/mcpStringUtils.ts` | MCP string utilities | moderate |
| `services/skills/registry.ts` | Skills registry | **complex** |
| `services/skills/loadSkillsDir.ts` | Loads skills from disk | moderate |
| `services/skills/bootstrap.ts` | Skills bootstrap | simple |
| `services/skills/budget.ts` | Skills budget management | moderate |
| `services/skills/conditional.ts` | Conditional skill loading | moderate |
| `services/skills/parseFrontmatter.ts` | Frontmatter parser | moderate |
| `types/types.ts` | Core type definitions | simple |
| `types/tool.ts` | Tool type definitions | simple |
| `types/message.ts` | Message type definitions | simple |
| `types/config.ts` | Config type definitions | simple |
| `types/task.ts` | Task type definitions | simple |
| `types/todo.ts` | Todo type definitions | simple |
| `types/mcp.ts` | MCP type definitions | simple |
| `utils/paths.ts` | Path utilities | **complex** |
| `utils/tokens.ts` | Token counting utilities | **complex** |
| `utils/worktree.ts` | Git worktree utilities | **complex** |
| `utils/taskOutput.ts` | Task output utilities | moderate |
| `utils/streamDebug.ts` | Stream debugging utilities | moderate |
| `utils/settings.ts` | Settings utilities | simple |
| `utils/loadEnv.ts` | Environment loading | moderate |
| `utils/log.ts` | Logging utilities | simple |
| `utils/config.ts` | Config utilities | simple |
| `constants/spinnerVerbs.ts` | Spinner verb list | moderate |
| `entrypoint/cli.ts` | CLI entry point | moderate |

### Scripts and Tests (`src/scripts/`)
| File | Description | Complexity |
|------|-------------|------------|
| `test-agents.ts` | Agent integration tests | **complex** |
| `test-mcp.ts` | MCP integration tests | **complex** |
| `test-sandbox.ts` | Sandbox integration tests | **complex** |
| `test-stage20.ts` | Stage 2.0 integration tests (1158 lines) | **complex** |
| `test-skills.ts` | Skills tests | moderate |
| `test-tasks.ts` | Task system tests | moderate |
| `test-tools.ts` | Tool tests | simple |
| `test-streaming.ts` | Streaming tests | simple |
| `smoke-sandbox.ts` | Sandbox smoke test | moderate |
| `smoke-bash-sandbox.ts` | Bash sandbox smoke test | moderate |

## Complexity Hotspots

These files have the highest complexity and should be approached carefully. They contain the most functions, the most lines, and the densest logic.

| File | Lines | Functions | Why It's Complex |
|------|-------|-----------|------------------|
| `src/ui/hooks/useAgentSession.ts` | 1051 | 3 | Main session orchestration — ties together agents, UI, and state |
| `src/core/queryEngine.ts` | 933 | 1 | The LLM query engine — manages streaming, tool dispatch, and response parsing |
| `src/scripts/test-stage20.ts` | 1158 | 5 | Comprehensive integration test covering the full system |
| `src/scripts/test-agents.ts` | 732 | 3 | Agent integration tests |
| `src/core/agenticLoop.ts` | 612 | 6 | The core autonomous execution loop |
| `src/tools/agentTool.ts` | 626 | 6 | Agent delegation tool — allows agents to spawn sub-agents |
| `src/services/mcp/client.ts` | 445 | 13 | MCP client with server lifecycle management |
| `src/permissions/permissions.ts` | 444 | 18 | Permission checking with many edge cases |
| `src/state/taskStore.ts` | 411 | 24 | Task state with the most functions of any file |
| `src/services/api/streaming.ts` | 400 | 1 | LLM streaming with complex event handling |
| `src/ui/components/ConversationView.tsx` | 386 | 9 | Main conversation rendering with many display modes |
| `src/session/storage.ts` | 362 | 16 | Session persistence with file I/O |
| `src/context/memory/memdir.ts` | 330 | 24 | Memory directory with 24 functions |
| `src/context/compaction.ts` | 318 | 11 | Conversation compaction logic |
| `src/agents/runAsyncAgent.ts` | 284 | 2 | Async agent execution |
| `src/agents/runAgent.ts` | 268 | 3 | Agent execution |
| `src/utils/worktree.ts` | 253 | 9 | Git worktree management |
| `src/state/asyncAgentStore.ts` | 236 | 11 | Async agent state management |
| `src/agents/loadAgentsDir.ts` | 210 | 9 | Agent loading from filesystem |
| `src/tools/bashTool.ts` | 216 | 4 | Bash execution with sandbox integration |
| `src/sandbox/buildProfile.ts` | 206 | 7 | Sandbox profile construction |
| `src/tools/taskUpdateTool.ts` | 200 | 3 | Task update logic |

**Tips for approaching complex files:**
- Start by reading the exported functions/types — understand the public API first
- Follow the call graph: which functions call which
- For `useAgentSession.ts`, understand the hook's dependencies before diving into its implementation
- For `queryEngine.ts` and `agenticLoop.ts`, trace the flow: query → stream → tool call → result → loop
- For store files (`taskStore.ts`, `asyncAgentStore.ts`), the pattern is consistent: state + actions + subscriptions
