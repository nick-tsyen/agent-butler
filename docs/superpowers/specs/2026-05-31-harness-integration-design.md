# Design Spec: Workspace Harness Integration for Agent Butler

**Date:** 2026-05-31  
**Status:** Draft / Awaiting Review  
**Topic:** Integrating Harness Engineering takeaways and template files into `agent_butler`.

---

## 1. Overview & Objectives

This document specifies how `agent_butler` will dynamically detect and support Harness-Managed Workspaces. Rather than relying solely on global or hidden configuration databases, `agent_butler` will prioritize local, repository-tracked template files (e.g., `feature_list.json`, `CLAUDE.md`, `decisions.md`, etc.) for session history, task list governance, and exit validation.

This design aligns the agent's runtime directly with the principles of **Harness Engineering**—making the repository the single source of truth, enforcing WIP=1 boundaries, and establishing strict gates against premature completion declarations.

---

## 2. Architectural Design

### 2.1 Workspace Detection
On startup, `agent_butler` will run a check to determine if it is operating inside a Harness-Managed Workspace.

- **Check Function:** `is_harness_workspace(cwd: str) -> bool`
- **Location:** `agent_butler/utils/paths.py`
- **Logic:**
  1. Traverse from `cwd` upward to the filesystem root.
  2. Check for the presence of any of the following key harness files in each directory:
     - `feature_list.json`
     - `CLAUDE.md`
     - `AGENTS.md`
  3. If found, save the parent path as the `harness_root` and flag the session as operating in **Harness Mode**.

---

## 3. Component Specifications

### 3.1 Task Store & Tool Integration (`feature_list.json`)
When Harness Mode is active, `agent_butler` task tools (`TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList`) will directly query and update the local `feature_list.json` in the workspace root instead of saving JSON files in `~/.agent-butler/tasks/`.

#### Task Status Mapping
`agent_butler` will map task statuses bidirectionally:

| agent_butler Status | feature_list.json Status |
| :--- | :--- |
| `pending` | `not_started` |
| `in_progress` | `in_progress` |
| `completed` | `passing` |
| `blocked` | `blocked` |

#### Enforcement Rules (WIP=1)
- **WIP=1 Constraint:** When calling `TaskUpdate` or `TaskCreate` to set a task status to `in_progress`, the tool will parse the entire `feature_list.json` first. If any other task is already in the `in_progress` state, the tool will fail with a clear message: 
  > `"Error: WIP=1 constraint is active. You cannot start a new feature until the active feature is passing or blocked."`
- **Evidence Requirement:** When marking a feature as `completed`/`passing`, the agent must provide an `evidence` array/description. This will be appended to the feature's `evidence` field in `feature_list.json`.

---

### 3.2 System Prompt & Clock-In
The prompt builder in `agent_butler/context/system_prompt.py` will read the workspace templates and inject them into the system prompt to guide model behavior.

#### Prompt Injection Blocks
1. **Instructions/Rules:** If `CLAUDE.md` or `AGENTS.md` is present, its content (with HTML comments stripped) will be loaded under `# Project Rules & Harness Instructions`.
2. **Design Decisions:** If `decisions.md` is present, it will be loaded under `# Architectural Decisions`.
3. **Session Progress:** If `claude-progress.md` is present, it will be loaded under `# Session History & Progress Tracker`.

#### Initialization Phase Gate (Clock-In)
- If `READY.md` is **not** present in the workspace root, the agent is considered to be in the **Initialization Phase**.
- The prompt builder will inject this strict instruction:
  > `[CRITICAL CONSTRAINT] READY.md was not found. You are in the Setup/Initialization Phase. Your only goal is to verify the test suite, create READY.md containing the startup readiness checklist, and commit a clean baseline. Do NOT write any feature/business code during this turn.`

---

### 3.3 Session Exit Gates (Clock-Out & Verification)
To prevent the agent from declaring victory on broken code, `agent_butler` will intercept session termination and run automated checks.

#### Exit Check Routine
When the agentic loop is about to exit (no more tool calls, final text output generated):
1. **Verification Trigger:** If a feature's status in `feature_list.json` has been updated to `passing` in the current session, the execution engine triggers the workspace verification command (specified in `CLAUDE.md` under `# Verification Commands` or via the feature's `verification_command` field).
2. **Gate Check:** 
   - If the verification command fails (non-zero exit code), the exit is aborted.
   - The failure details are appended as a system message:
     > `[SYSTEM NOTICE] Exit gate failed. The verification command <command> failed with exit code <status>. You must fix the code, run verification, and record the output before declaring victory.`
   - The agent is forced to run another loop turn to address the failure.
3. **Hygiene Check:** If `clean-state-checklist.md` exists, the agent is prompted to verify that all temporary debug artifacts (e.g. log output files) are removed, and that `claude-progress.md` contains an updated session record.

---

## 4. Testing Plan

To verify this integration, a test suite will be added to `tests/test_harness_integration.py` containing:
1. **Detection Tests:** Verify that `is_harness_workspace` correctly flags projects containing `feature_list.json` or `CLAUDE.md`.
2. **Task Mapping Tests:** Mock a `feature_list.json` and ensure `TaskCreate`, `TaskUpdate`, and `TaskList` read and write to it with status conversions.
3. **WIP=1 Rule Tests:** Verify that trying to set two tasks to `in_progress` in `feature_list.json` raises a validation error.
4. **Exit Gate Tests:** Verify that a failing verification command halts the agentic loop exit and injects the failure message.
