# Workspace Harness Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incorporate Harness Engineering guidelines and template files into `agent_butler` by dynamically detecting harness workspaces, redirecting task tools to `feature_list.json` (enforcing WIP=1), loading context files into the system prompt, and gating session completion on verification test suite execution.

**Architecture:** Update paths module to support workspace detection, implement `feature_list.json` data mapping/redirection in `task_store.py`, inject context templates in the prompt generator, and run verification subprocess gates on loop completion.

**Tech Stack:** Python 3.10+, Pytest, Pydantic, standard library JSON & subprocess.

---

### Task 1: Workspace Detection Helpers

**Files:**
- Modify: `agent_butler/utils/paths.py`
- Create: `tests/test_harness_integration.py`

- [ ] **Step 1: Write the failing test**

Write the detection tests in `tests/test_harness_integration.py`:
```python
import os
import tempfile
from pathlib import Path
from agent_butler.utils.paths import get_harness_root, is_harness_workspace

def test_harness_workspace_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub_dir = tmp_path / "src" / "api"
        sub_dir.mkdir(parents=True)
        
        # Initially not a harness workspace
        assert not is_harness_workspace(str(sub_dir))
        assert get_harness_root(str(sub_dir)) is None
        
        # Add CLAUDE.md to simulate harness workspace root
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text("# Project rules")
        
        # Detection should traverse up and find it
        assert is_harness_workspace(str(sub_dir))
        assert Path(get_harness_root(str(sub_dir))) == tmp_path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_integration.py -v`
Expected: Fail with `ImportError: cannot import name 'get_harness_root'` or similar.

- [ ] **Step 3: Implement detection helpers**

Add the detection helpers to `agent_butler/utils/paths.py`:
```python
def get_harness_root(cwd: str) -> Path | None:
    current = Path(cwd).resolve()
    while True:
        if (current / "feature_list.json").is_file() or (current / "CLAUDE.md").is_file() or (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None

def is_harness_workspace(cwd: str) -> bool:
    return get_harness_root(cwd) is not None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_butler/utils/paths.py tests/test_harness_integration.py
git commit -m "feat: add workspace harness detection helpers"
```

---

### Task 2: Harness Template Injections and Setup Gate

**Files:**
- Modify: `agent_butler/context/system_prompt.py`
- Modify: `tests/test_harness_integration.py`

- [ ] **Step 1: Write the failing test**

Add prompt injection tests in `tests/test_harness_integration.py`:
```python
from agent_butler.context.system_prompt import build_system_prompt

def test_system_prompt_harness_injection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create context files
        (tmp_path / "CLAUDE.md").write_text("CLAUDE_RULES")
        (tmp_path / "decisions.md").write_text("DECISIONS_LIST")
        (tmp_path / "claude-progress.md").write_text("PROGRESS_STATE")
        
        # Test without READY.md (should show initialization constraint)
        prompt = build_system_prompt(str(tmp_path), "test-model", [], [], [])
        assert "CLAUDE_RULES" in prompt
        assert "DECISIONS_LIST" in prompt
        assert "PROGRESS_STATE" in prompt
        assert "[CRITICAL CONSTRAINT] READY.md was not found" in prompt
        
        # Test with READY.md (should not show constraint)
        (tmp_path / "READY.md").write_text("READY")
        prompt_ready = build_system_prompt(str(tmp_path), "test-model", [], [], [])
        assert "[CRITICAL CONSTRAINT] READY.md was not found" not in prompt_ready
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_integration.py -k test_system_prompt_harness_injection -v`
Expected: Fail because prompt contents do not have the injected text.

- [ ] **Step 3: Implement prompt loading**

Update `build_system_prompt` in `agent_butler/context/system_prompt.py` to check for harness root and clean/load files:
```python
import re

def _read_clean_file(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8")
        # Strip html comments
        cleaned = re.sub(r"<!--[\s\S]*?-->", "", raw).strip()
        return cleaned or None
    except Exception:
        return None
```
Modify `build_system_prompt` implementation to load files and format them:
```python
    # Load harness files
    from ..utils.paths import get_harness_root
    harness_root = get_harness_root(cwd)
    harness_sections = []
    
    if harness_root:
        # Check READY.md for initialization phase
        ready_path = harness_root / "READY.md"
        if not ready_path.is_file():
            harness_sections.append(
                "[CRITICAL CONSTRAINT] READY.md was not found in the workspace root. "
                "You are currently in the Setup/Initialization Phase. Your only goal is to "
                "verify the test suite, create READY.md containing the startup readiness checklist, "
                "and commit a clean baseline. Do NOT write any feature or business code during this turn."
            )
            
        # Load CLAUDE.md or AGENTS.md
        rules_path = harness_root / "CLAUDE.md"
        if not rules_path.is_file():
            rules_path = harness_root / "AGENTS.md"
        if rules_path.is_file():
            content = _read_clean_file(rules_path)
            if content:
                harness_sections.append(f"# Project Rules & Harness Instructions (from {rules_path.name}):\n{content}")
                
        # Load decisions.md
        dec_path = harness_root / "decisions.md"
        if dec_path.is_file():
            content = _read_clean_file(dec_path)
            if content:
                harness_sections.append(f"# Architectural Decisions (from decisions.md):\n{content}")
                
        # Load claude-progress.md
        prog_path = harness_root / "claude-progress.md"
        if not prog_path.is_file():
            prog_path = harness_root / "PROGRESS.md"
        if prog_path.is_file():
            content = _read_clean_file(prog_path)
            if content:
                harness_sections.append(f"# Session History & Progress Tracker (from {prog_path.name}):\n{content}")
```
Add `harness_sections` array to the `dynamic_parts` of the system prompt in `build_system_prompt`:
```python
    # In build_system_prompt:
    dynamic_parts: list[str] = [
        SYSTEM_PROMPT_DYNAMIC_START,
        _format_environment_context(environment_context),
    ]
    if harness_sections:
        dynamic_parts.extend(harness_sections)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness_integration.py -k test_system_prompt_harness_injection -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_butler/context/system_prompt.py tests/test_harness_integration.py
git commit -m "feat: inject CLAUDE.md, decisions, progress and setup gate into system prompt"
```

---

### Task 3: Directing Task Store to feature_list.json with WIP=1 Enforcement

**Files:**
- Modify: `agent_butler/state/task_store.py`
- Modify: `agent_butler/tools/task_update_tool.py`
- Modify: `tests/test_harness_integration.py`

- [ ] **Step 1: Write the failing test**

Add task store redirection and WIP=1 enforcement tests in `tests/test_harness_integration.py`:
```python
import pytest
from agent_butler.state.task_store import create_task, update_task, list_tasks, get_task

async def test_task_store_feature_list_redirection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        feature_list_file = tmp_path / "feature_list.json"
        feature_list_file.write_text(json.dumps({
            "project": "test-project",
            "features": [
                {
                    "id": "f1",
                    "title": "First feature",
                    "behavior": "First behavior",
                    "status": "not_started"
                },
                {
                    "id": "f2",
                    "title": "Second feature",
                    "behavior": "Second behavior",
                    "status": "in_progress"
                }
            ]
        }))
        
        # Change cwd to tmpdir to trigger harness mode redirection
        orig_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # list_tasks
            tasks = await list_tasks("session-1")
            assert len(tasks) == 2
            assert tasks[0]["id"] == "f1"
            assert tasks[0]["status"] == "pending"
            assert tasks[1]["status"] == "in_progress"
            
            # get_task
            task_f1 = await get_task("session-1", "f1")
            assert task_f1["subject"] == "First feature"
            
            # WIP=1 Constraint check: setting f1 to in_progress should raise error
            with pytest.raises(ValueError, match="WIP=1 constraint is active"):
                await update_task("session-1", "f1", {"status": "in_progress"})
                
            # Finish f2 first
            await update_task("session-1", "f2", {"status": "completed"})
            
            # Now f1 can be set to in_progress
            ok = await update_task("session-1", "f1", {"status": "in_progress"})
            assert ok
            
            # Verify file updated
            updated_data = json.loads(feature_list_file.read_text())
            assert updated_data["features"][0]["status"] == "in_progress"
            assert updated_data["features"][1]["status"] == "passing"
        finally:
            os.chdir(orig_cwd)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_integration.py -k test_task_store_feature_list_redirection -v`
Expected: Fail due to no `ValueError` raised and no redirection implemented.

- [ ] **Step 3: Implement task store redirection and WIP=1 constraint**

Update `agent_butler/state/task_store.py`:
- Import `get_harness_root` from `..utils.paths`.
- Implement local helper functions to read and write mapped `feature_list.json` structures.
- Enforce the WIP=1 restriction:
```python
# Insert into agent_butler/state/task_store.py

def _get_harness_feature_list_path() -> Path | None:
    import os
    from ..utils.paths import get_harness_root
    harness_root = get_harness_root(os.getcwd())
    if harness_root:
        p = harness_root / "feature_list.json"
        if p.is_file():
            return p
    return None

def _map_feature_to_task(f: dict[str, Any]) -> dict[str, Any]:
    status_map = {
        "not_started": "pending",
        "in_progress": "in_progress",
        "passing": "completed",
        "blocked": "blocked"
    }
    return {
        "id": f.get("id"),
        "subject": f.get("title", ""),
        "description": f.get("behavior", ""),
        "status": status_map.get(f.get("status"), "pending"),
        "blocks": f.get("blocks", []),
        "blocked_by": f.get("blocked_by", []),
        "metadata": {
            "priority": f.get("priority"),
            "area": f.get("area"),
            "verification_command": f.get("verification_command"),
            "verification": f.get("verification"),
            "evidence": f.get("evidence"),
            "notes": f.get("notes")
        }
    }
```
Redefine `create_task`, `get_task`, `update_task`, `delete_task`, `list_tasks`, and `block_task` in `agent_butler/state/task_store.py` to route to `feature_list.json` if it exists.
For example, inside `update_task`:
```python
async def update_task(list_id: str, task_id: str, updates: dict[str, Any]) -> bool:
    fl_path = _get_harness_feature_list_path()
    if fl_path:
        lock = FileLock(str(fl_path.with_name(".feature_list.lock")))
        with lock:
            data = json.loads(fl_path.read_text(encoding="utf-8"))
            features = data.get("features", [])
            target = None
            for f in features:
                if f.get("id") == task_id:
                    target = f
                    break
            if not target:
                return False
                
            # Status mapping
            new_status_raw = updates.get("status")
            if new_status_raw:
                status_map = {
                    "pending": "not_started",
                    "in_progress": "in_progress",
                    "completed": "passing",
                    "blocked": "blocked"
                }
                new_status = status_map.get(new_status_raw)
                
                # Enforce WIP=1
                if new_status == "in_progress":
                    for f in features:
                        if f.get("id") != task_id and f.get("status") == "in_progress":
                            raise ValueError("WIP=1 constraint is active. You cannot start a new feature until the active feature is passing or blocked.")
                            
                target["status"] = new_status
                
            if "subject" in updates:
                target["title"] = updates["subject"]
            if "description" in updates:
                target["behavior"] = updates["description"]
            
            # Merge metadata
            meta = updates.get("metadata")
            if isinstance(meta, dict):
                for k in ("verification_command", "verification", "notes"):
                    if k in meta:
                        target[k] = meta[k]
                if "evidence" in meta:
                    ev = target.setdefault("evidence", [])
                    if isinstance(meta["evidence"], list):
                        ev.extend(meta["evidence"])
                    else:
                        ev.append(str(meta["evidence"]))
                        
            fl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _notify_task_change(list_id)
        return True
```
Modify `TaskUpdateTool.call` in `agent_butler/tools/task_update_tool.py` to catch `ValueError`:
```python
        # Modify line 90 in agent_butler/tools/task_update_tool.py:
        if updates:
            try:
                await update_task(task_list_id, task_id, updates)
            except ValueError as exc:
                return ToolResult(content=f"Error: {exc}", is_error=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness_integration.py -k test_task_store_feature_list_redirection -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_butler/state/task_store.py agent_butler/tools/task_update_tool.py tests/test_harness_integration.py
git commit -m "feat: redirect TaskStore tasks to feature_list.json and enforce WIP=1"
```

---

### Task 4: Loop Exit Verification Gate Check

**Files:**
- Modify: `agent_butler/state/task_store.py`
- Modify: `agent_butler/core/agentic_loop.py`
- Modify: `agent_butler/ui/session_hook.py`
- Modify: `tests/test_harness_integration.py`

- [ ] **Step 1: Write the failing test**

Add exit gate tests in `tests/test_harness_integration.py`:
```python
from agent_butler.state.task_store import check_exit_gate

async def test_exit_gate_verification_fail():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "CLAUDE.md").write_text("Full verify: `exit 1`")
        (tmp_path / "feature_list.json").write_text(json.dumps({
            "features": [{"id": "f1", "status": "passing"}]
        }))
        
        # Running check_exit_gate should capture verification failure
        err = await check_exit_gate(str(tmp_path))
        assert err is not None
        assert "Exit gate failed" in err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_integration.py -k test_exit_gate_verification_fail -v`
Expected: Fail (no `check_exit_gate` defined).

- [ ] **Step 3: Implement exit gate check and loop integration**

Implement `check_exit_gate` in `agent_butler/state/task_store.py`:
```python
async def check_exit_gate(harness_root: str) -> str | None:
    feature_list_path = Path(harness_root) / "feature_list.json"
    if not feature_list_path.is_file():
        return None
    try:
        data = json.loads(feature_list_path.read_text(encoding="utf-8"))
    except Exception:
        return None
        
    # Check if any feature status is 'passing'
    has_passing = any(f.get("status") == "passing" for f in data.get("features", []))
    if not has_passing:
        return None
        
    # Resolve verification command from CLAUDE.md / AGENTS.md
    rules_path = Path(harness_root) / "CLAUDE.md"
    if not rules_path.is_file():
        rules_path = Path(harness_root) / "AGENTS.md"
        
    cmd = None
    if rules_path.is_file():
        text = rules_path.read_text(encoding="utf-8")
        m = re.search(r"Full verify:\s*`([^`]+)`", text)
        if not m:
            m = re.search(r"Full verification:\s*`([^`]+)`", text)
        if not m:
            m = re.search(r"Full verify:\s*<([^>]+)>", text)
        if not m:
            m = re.search(r"Full verification:\s*<([^>]+)>", text)
        if m:
            cmd = m.group(1).strip()
            
    if not cmd:
        for f in data.get("features", []):
            if f.get("status") == "passing" and f.get("verification_command"):
                cmd = f.get("verification_command")
                break
                
    if cmd:
        import subprocess
        try:
            res = subprocess.run(cmd, shell=True, cwd=harness_root, capture_output=True, text=True)
            if res.returncode != 0:
                return (
                    f"[SYSTEM NOTICE] Exit gate failed. The verification command `{cmd}` failed with exit code {res.returncode}.\n"
                    f"Stdout:\n{res.stdout}\n"
                    f"Stderr:\n{res.stderr}\n"
                    f"You must fix the code, run verification, and record the output before declaring victory."
                )
        except Exception as e:
            return f"[SYSTEM NOTICE] Exit gate check failed while running verification command `{cmd}`: {e}"
            
    return None
```
Hook `check_exit_gate` into `agentic_loop.py` around line 223:
```python
        # In agent_butler/core/agentic_loop.py, inside query():
        if not tool_use_blocks:
            from ..utils.paths import get_harness_root
            harness_root = get_harness_root(cwd)
            exit_error = None
            if harness_root:
                from ..state.task_store import check_exit_gate
                exit_error = await check_exit_gate(str(harness_root))
                
            if exit_error:
                current_messages.append({"role": "user", "content": exit_error})
                continue
```
Hook `check_exit_gate` into `session_hook.py` around line 214:
```python
            # In agent_butler/ui/session_hook.py, inside _run_agent_loop():
            if not tool_calls:
                from ..utils.paths import get_harness_root
                harness_root = get_harness_root(self._cwd)
                exit_error = None
                if harness_root:
                    from ..state.task_store import check_exit_gate
                    exit_error = await check_exit_gate(str(harness_root))
                    
                if exit_error:
                    self._state.messages.append(UserMessage(content=exit_error))
                    continue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness_integration.py -v`
Expected: ALL TESTS PASS

- [ ] **Step 5: Commit**

```bash
git add agent_butler/state/task_store.py agent_butler/core/agentic_loop.py agent_butler/ui/session_hook.py tests/test_harness_integration.py
git commit -m "feat: enforce exit gate verification checks on loop completion"
```
