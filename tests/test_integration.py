"""Integration tests covering cross-module interactions."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pytest

from agent_butler.types.message import (
    AssistantMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    Usage,
)
from agent_butler.types.task import Task
from agent_butler.types.todo import TodoItem
from agent_butler.types.skill import Skill, SkillFrontmatter
from agent_butler.types.tool import ToolContext, ToolResult


# ── Helpers ──────────────────────────────────────────────────────────

class _StubTool:
    """Minimal tool for integration testing."""

    def __init__(
        self,
        name: str = "Stub",
        read_only: bool = True,
        enabled: bool = True,
        concurrency_safe: bool = False,
    ) -> None:
        self._name = name
        self._read_only = read_only
        self._enabled = enabled
        self._concurrency_safe = concurrency_safe
        self.call_log: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Stub tool {self._name}"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        self.call_log.append({"input": input_data, "context_cwd": context.cwd})
        return ToolResult(content=f"ok:{self._name}")

    def is_read_only(self) -> bool:
        return self._read_only

    def is_enabled(self) -> bool:
        return self._enabled

    def is_concurrency_safe(self, input_data: dict[str, Any] | None = None) -> bool:
        return self._concurrency_safe


# ── Task Store CRUD ──────────────────────────────────────────────────

class TestTaskStoreIntegration:
    """Test task store end-to-end: create → read → update → block → delete."""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent_butler.utils.paths.get_tasks_root", lambda: str(tmp_path / "tasks"))
        import agent_butler.state.task_store
        monkeypatch.setattr("agent_butler.state.task_store.get_tasks_root", lambda: str(tmp_path / "tasks"))
        monkeypatch.setattr("agent_butler.state.task_store._get_harness_feature_list_path", lambda: None)

        from agent_butler.state.task_store import (
            block_task,
            create_task,
            delete_task,
            get_task,
            get_task_list_id,
            list_tasks,
            update_task,
        )

        list_id = get_task_list_id("test-session")

        # Create two tasks
        id1 = await create_task(list_id, {"subject": "Task A", "description": "First task"})
        id2 = await create_task(list_id, {"subject": "Task B", "description": "Second task"})
        assert id1 != id2

        # Read back
        t1 = await get_task(list_id, id1)
        assert t1 is not None
        assert t1["subject"] == "Task A"
        assert t1["status"] == "pending"

        # Update status
        ok = await update_task(list_id, id1, {"status": "in_progress"})
        assert ok is True
        t1 = await get_task(list_id, id1)
        assert t1["status"] == "in_progress"

        # Block task2 by task1
        ok = await block_task(list_id, id1, id2)
        assert ok is True
        t1 = await get_task(list_id, id1)
        t2 = await get_task(list_id, id2)
        assert id2 in t1["blocks"]
        assert id1 in t2["blocked_by"]

        # List all
        all_tasks = await list_tasks(list_id)
        assert len(all_tasks) == 2

        # Delete task1
        ok = await delete_task(list_id, id1)
        assert ok is True
        assert await get_task(list_id, id1) is None

        # Non-existent
        ok = await delete_task(list_id, "nonexistent")
        assert ok is False

    @pytest.mark.asyncio
    async def test_task_list_id_sanitization(self) -> None:
        from agent_butler.state.task_store import get_task_list_id
        assert "/" not in get_task_list_id("session/with/slashes")
        assert "\\" not in get_task_list_id("session\\with\\backslashes")


# ── Todo Store ───────────────────────────────────────────────────────

class TestTodoStoreIntegration:
    def test_set_and_get_todos(self) -> None:
        from agent_butler.state.todo_store import get_todos, set_todos

        set_todos("sess-1", [
            {"content": "Write tests", "status": "in_progress", "activeForm": "Writing tests"},
            {"content": "Run tests", "status": "pending", "activeForm": "Running tests"},
        ])
        todos = get_todos("sess-1")
        assert len(todos) == 2
        assert todos[0]["content"] == "Write tests"

    def test_session_isolation(self) -> None:
        from agent_butler.state.todo_store import get_todos, set_todos

        set_todos("sess-a", [{"content": "A", "status": "pending", "activeForm": "A-ing"}])
        set_todos("sess-b", [{"content": "B", "status": "pending", "activeForm": "B-ing"}])
        assert len(get_todos("sess-a")) == 1
        assert len(get_todos("sess-b")) == 1
        assert get_todos("sess-a")[0]["content"] == "A"


# ── Task Mode Store ──────────────────────────────────────────────────

class TestTaskModeStoreIntegration:
    def test_default_modes(self) -> None:
        from agent_butler.state.task_mode_store import is_task_mode_enabled, is_todo_mode_enabled, set_task_mode

        # Reset to defaults
        set_task_mode("task")
        assert is_task_mode_enabled() is True
        assert is_todo_mode_enabled() is False

        set_task_mode("todo")
        assert is_task_mode_enabled() is False
        assert is_todo_mode_enabled() is True

        # Restore
        set_task_mode("task")


# ── Notification Store ───────────────────────────────────────────────

class TestNotificationStoreIntegration:
    def test_notification_lifecycle(self) -> None:
        from agent_butler.state.notification_store import (
            add_notification,
            clear_notifications,
            get_pending_notifications,
        )

        clear_notifications()
        add_notification({"type": "agent_done", "agent_id": "abc"})
        add_notification({"type": "agent_done", "agent_id": "def"})

        pending = get_pending_notifications()
        assert len(pending) == 2

        clear_notifications()
        assert len(get_pending_notifications()) == 0


# ── Async Agent Store ────────────────────────────────────────────────

class TestAsyncAgentStoreIntegration:
    def test_register_and_complete(self) -> None:
        from agent_butler.state.async_agent_store import (
            complete_async_agent,
            get_async_agent,
            register_async_agent,
        )

        entry = register_async_agent({
            "agent_id": "test-agent-1",
            "agent_type": "explore",
            "prompt": "find all tests",
            "output_file": "/tmp/test.output",
        })
        assert entry["agent_id"] == "test-agent-1"

        agent = get_async_agent("test-agent-1")
        assert agent is not None
        assert agent["agent_type"] == "explore"

        complete_async_agent("test-agent-1", {"final_text": "done"})
        agent = get_async_agent("test-agent-1")
        assert agent.get("result", {}).get("final_text") == "done"


# ── Sub-Agent Progress ───────────────────────────────────────────────

class TestSubAgentProgressIntegration:
    def test_progress_lifecycle(self) -> None:
        from agent_butler.state.sub_agent_progress import (
            complete_sub_agent_progress,
            get_sub_agent_progress,
            start_sub_agent_progress,
            update_sub_agent_progress,
        )

        start_sub_agent_progress("key-1", {"agent_type": "explore"})
        update_sub_agent_progress("key-1", {"last_tool_name": "Read", "total_tokens": 500})
        progress = get_sub_agent_progress("key-1")
        assert progress is not None
        # Updates are stored in the updates list
        assert len(progress["updates"]) == 1
        assert progress["updates"][0]["last_tool_name"] == "Read"

        complete_sub_agent_progress("key-1", {"reason": "completed", "duration_ms": 1000})
        progress = get_sub_agent_progress("key-1")
        assert progress["status"] == "completed"
        assert progress["result"]["reason"] == "completed"


# ── Agent Registry ───────────────────────────────────────────────────

class TestAgentRegistryIntegration:
    def test_register_find_list(self) -> None:
        from agent_butler.agents.registry import (
            clear_registry,
            find_agent,
            get_all_agents,
            register_agent,
        )
        from agent_butler.agents.types import AgentDefinition

        clear_registry()
        register_agent(AgentDefinition(
            agent_type="test-agent",
            description="A test agent",
            system_prompt="You are a test.",
        ))
        register_agent(AgentDefinition(
            agent_type="test-agent-2",
            description="Another test agent",
            system_prompt="You are another test.",
        ))

        assert find_agent("test-agent") is not None
        assert find_agent("nonexistent") is None
        assert len(get_all_agents()) == 2

        clear_registry()

    def test_built_in_agents_load(self) -> None:
        from agent_butler.agents.built_in.explore import AGENT_DEFINITION as EXPLORE
        from agent_butler.agents.built_in.general_purpose import AGENT_DEFINITION as GP

        assert EXPLORE.agent_type == "explore"
        assert "Read" in EXPLORE.tools_allow
        assert GP.agent_type == "general-purpose"
        assert GP.max_turns == 100


# ── Skills Registry ──────────────────────────────────────────────────

class TestSkillsRegistryIntegration:
    def test_register_find_conditional(self) -> None:
        from agent_butler.services.skills.registry import (
            activate_conditional,
            clear_skills,
            find_skill,
            get_all_skills,
            list_conditional_skills,
            register_skill,
        )

        clear_skills()

        # Regular skill
        register_skill(Skill(
            name="test-skill",
            description="A test skill",
            body="Do the thing",
            file_path="/tmp/SKILL.md",
            base_dir="/tmp",
            source="user",
            frontmatter=SkillFrontmatter(allowed_tools=[]),
        ))

        # Conditional skill
        register_skill(Skill(
            name="cond-skill",
            description="Conditional",
            body="Conditional body",
            file_path="/tmp2/SKILL.md",
            base_dir="/tmp2",
            source="project",
            frontmatter=SkillFrontmatter(allowed_tools=[], paths=["*.test.ts"]),
        ))

        assert find_skill("test-skill") is not None
        assert find_skill("cond-skill") is not None
        assert len(list_conditional_skills()) == 1
        assert len(get_all_skills()) == 2

        # Activate conditional
        ok = activate_conditional("cond-skill")
        assert ok is True
        assert len(list_conditional_skills()) == 0
        assert find_skill("cond-skill") is not None

        clear_skills()


# ── Parse Frontmatter ────────────────────────────────────────────────

class TestParseFrontmatterIntegration:
    def test_parse_yaml_frontmatter(self) -> None:
        from agent_butler.services.skills.parse_frontmatter import parse_frontmatter

        content = """---
name: test-skill
description: A test skill
allowedTools:
  - Read
  - Bash
---

# Test Skill

Do the thing here.
"""
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "test-skill"
        assert fm["description"] == "A test skill"
        assert "Read" in fm.get("allowedTools", [])
        assert "Do the thing here." in body


# ── Session Storage ──────────────────────────────────────────────────

class TestSessionStorageIntegration:
    @pytest.mark.asyncio
    async def test_save_load_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent_butler.utils.paths.get_projects_root", lambda: str(tmp_path / "projects"))

        from agent_butler.session.storage import list_sessions, load_session, save_session

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        await save_session("test-session-1", messages)

        loaded = await load_session("test-session-1")
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["role"] == "user"

        sessions = await list_sessions()
        assert "test-session-1" in sessions


# ── Sandbox + Permissions Integration ────────────────────────────────

class TestSandboxPermissionsIntegration:
    def test_sandbox_auto_allow_with_deny_rule(self) -> None:
        from agent_butler.sandbox.settings import ResolvedSandboxSettings
        from agent_butler.sandbox.should_use import should_use_sandbox

        # Sandbox enabled but command excluded
        settings = ResolvedSandboxSettings(enabled=True, excluded_commands=["docker"])
        assert should_use_sandbox({"command": "echo hi"}, settings) is True
        assert should_use_sandbox({"command": "docker build ."}, settings) is False

    def test_permission_deny_overrides_sandbox_allow(self) -> None:
        from agent_butler.permissions.permissions import PermissionSettings, matches_permission_rule

        # Deny rule matches
        settings = PermissionSettings(deny=["Bash(rm *)"])
        assert matches_permission_rule("Bash(rm *)", "Bash", {"command": "rm -rf /"}) is True

    def test_read_only_command_detection(self) -> None:
        from agent_butler.tools.bash_tool import is_read_only_command

        assert is_read_only_command("ls -la") is True
        assert is_read_only_command("cat file.txt") is True
        assert is_read_only_command("git status") is True
        assert is_read_only_command("npm install") is False
        assert is_read_only_command("rm -rf /") is False

    def test_compound_command_read_only(self) -> None:
        from agent_butler.tools.bash_tool import is_read_only_command

        # All segments read-only
        assert is_read_only_command("ls && cat foo") is True
        # Mixed — not read-only
        assert is_read_only_command("ls && rm foo") is False


# ── Split Command ────────────────────────────────────────────────────

class TestSplitCommandIntegration:
    def test_splits_operators(self) -> None:
        from agent_butler.sandbox.split_command import split_command

        assert len(split_command("echo a && echo b")) == 2
        assert len(split_command("echo a || echo b")) == 2
        assert len(split_command("echo a | grep b")) == 2
        assert len(split_command("echo a")) == 1

    def test_respects_quotes(self) -> None:
        from agent_butler.sandbox.split_command import split_command

        segments = split_command('echo "a && b" && echo c')
        assert len(segments) == 2
        assert "a && b" in segments[0]


# ── Violations ───────────────────────────────────────────────────────

class TestViolationsIntegration:
    def test_annotate_and_strip(self) -> None:
        from agent_butler.sandbox.violations import (
            annotate_stderr_with_sandbox_failures,
            has_sandbox_violation_tag,
            looks_like_sandbox_violation,
            remove_sandbox_violation_tags,
        )

        assert looks_like_sandbox_violation("Operation not permitted") is True
        assert looks_like_sandbox_violation("some random error") is False

        annotated = annotate_stderr_with_sandbox_failures("Operation not permitted", 1)
        assert has_sandbox_violation_tag(annotated) is True

        stripped = remove_sandbox_violation_tags(annotated)
        assert has_sandbox_violation_tag(stripped) is False

        # No annotation on success
        assert annotate_stderr_with_sandbox_failures("ok", 0) == "ok"


# ── Path Utils ───────────────────────────────────────────────────────

class TestPathUtilsIntegration:
    def test_resolve_inside_allowed_root(self, tmp_path: Path) -> None:
        from agent_butler.tools.path_utils import resolve_workspace_path

        resolved = resolve_workspace_path("test.txt", str(tmp_path))
        assert str(tmp_path) in resolved

    def test_reject_outside_allowed_root(self, tmp_path: Path) -> None:
        from agent_butler.tools.path_utils import resolve_workspace_path

        with pytest.raises(ValueError, match="outside the allowed roots"):
            resolve_workspace_path("/etc/passwd", str(tmp_path))

    def test_expand_home(self) -> None:
        from agent_butler.tools.path_utils import expand_home

        home = os.environ.get("HOME", "")
        result = expand_home("~/test")
        assert result == f"{home}/test"


# ── Worktree Utilities ───────────────────────────────────────────────

class TestWorktreeIntegration:
    def test_branch_name_and_path(self) -> None:
        from agent_butler.utils.worktree import worktree_branch_name, worktree_path_for

        assert worktree_branch_name("agent-explore") == "worktree-agent-explore"
        assert "agent" in worktree_path_for("/repo", "agent-1")


# ── Token Estimation ─────────────────────────────────────────────────

class TestTokenEstimationIntegration:
    def test_estimate_message_tokens(self) -> None:
        from agent_butler.utils.tokens import (
            estimate_message_tokens,
            get_context_window_for_model,
            get_effective_context_window_size,
        )

        tokens = estimate_message_tokens({"role": "user", "content": "Hello world"})
        assert tokens > 0

        window = get_context_window_for_model("claude-sonnet-4-20250514")
        assert window == 200_000

        effective = get_effective_context_window_size("claude-sonnet-4-20250514")
        assert effective < window

    def test_budget_snapshot(self) -> None:
        from agent_butler.utils.tokens import build_token_budget_snapshot

        messages = [{"role": "user", "content": "Hello"}]
        snapshot = build_token_budget_snapshot(messages, model="claude-sonnet-4-20250514")
        assert snapshot.context_window == 200_000
        assert snapshot.auto_compact_threshold > 0


# ── Memory Directory ─────────────────────────────────────────────────

class TestMemoryIntegration:
    @pytest.mark.asyncio
    async def test_write_and_read_memory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent_butler.utils.paths.get_projects_root", lambda: str(tmp_path / "projects"))
        monkeypatch.setattr("agent_butler.utils.paths.get_agent_butler_home", lambda: str(tmp_path / "agent-butler"))

        from agent_butler.context.memory.memdir import read_project_memories, write_project_memory

        result = write_project_memory(
            cwd=str(tmp_path),
            name="test-memory",
            description="A test memory",
            type="project",
            content="# Test\nThis is a test memory.",
        )
        assert result["fileName"]

        memories = read_project_memories(str(tmp_path))
        assert len(memories) >= 1


# ── Plans ────────────────────────────────────────────────────────────

class TestPlansIntegration:
    @pytest.mark.asyncio
    async def test_plan_lifecycle(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent_butler.utils.paths.get_plans_root", lambda: str(tmp_path / "plans"))

        from agent_butler.context.plans import ensure_plans_directory, get_plan_file_path, read_plan, write_plan

        ensure_plans_directory()
        plan_path = get_plan_file_path()
        assert plan_path

        write_plan("# My Plan\nDo the thing.")
        content = read_plan()
        assert content is not None
        assert "My Plan" in content


# ── Tool Registry + Execution ────────────────────────────────────────

class TestToolRegistryExecutionIntegration:
    @pytest.mark.asyncio
    async def test_register_and_call_tool(self) -> None:
        from agent_butler.tools.registry import get_all_tools, register_builtin_tools

        tool = _StubTool("IntegrationTest", read_only=True)
        register_builtin_tools([tool])

        found = None
        for t in get_all_tools():
            if t.name == "IntegrationTest":
                found = t
                break

        assert found is not None
        result = await found.call({"key": "value"}, ToolContext(cwd="/tmp"))
        assert result.content == "ok:IntegrationTest"
        assert len(tool.call_log) == 1

    @pytest.mark.asyncio
    async def test_concurrency_safe_batching(self) -> None:
        from agent_butler.core.agentic_loop import partition_tool_calls

        safe_tool = {"name": "Read", "input": {}, "id": "1"}
        unsafe_tool = {"name": "Write", "input": {}, "id": "2"}

        # Need actual tool objects for partition
        from agent_butler.tools.registry import register_builtin_tools
        read_tool = _StubTool("Read", concurrency_safe=True)
        write_tool = _StubTool("Write", concurrency_safe=False)
        register_builtin_tools([read_tool, write_tool])

        batches = partition_tool_calls(
            [safe_tool, safe_tool, unsafe_tool, safe_tool],
            [read_tool, write_tool],
        )
        # Should be: [batch of 2 safe], [1 unsafe], [1 safe]
        assert len(batches) == 3


# ── Content Block Types ──────────────────────────────────────────────

class TestContentBlockIntegration:
    def test_text_block(self) -> None:
        block = TextBlock(text="hello")
        assert block.type == "text"
        dumped = block.model_dump()
        assert dumped["text"] == "hello"

    def test_tool_use_block(self) -> None:
        block = ToolUseBlock(id="tu-1", name="Read", input={"file_path": "/tmp/x"})
        assert block.type == "tool_use"
        assert block.name == "Read"

    def test_tool_result_block(self) -> None:
        block = ToolResultBlock(tool_use_id="tu-1", content="file content")
        assert block.type == "tool_result"
        assert block.tool_use_id == "tu-1"

    def test_thinking_block(self) -> None:
        block = ThinkingBlock(thinking="Let me think...", signature="sig123")
        assert block.type == "thinking"
        assert block.signature == "sig123"

    def test_assistant_message_with_blocks(self) -> None:
        msg = AssistantMessage(content=[
            TextBlock(text="Here's what I found:"),
            ToolUseBlock(id="tu-1", name="Read", input={}),
        ])
        assert msg.role == "assistant"
        assert len(msg.content) == 2


# ── Usage Tracking ───────────────────────────────────────────────────

class TestUsageIntegration:
    def test_usage_accumulation(self) -> None:
        u1 = Usage(input_tokens=100, output_tokens=50, cache_read_input_tokens=10)
        u2 = Usage(input_tokens=200, output_tokens=80, cache_creation_input_tokens=5)

        total_in = u1.input_tokens + u2.input_tokens
        total_out = u1.output_tokens + u2.output_tokens
        assert total_in == 300
        assert total_out == 130

    def test_usage_serialization(self) -> None:
        u = Usage(input_tokens=100, output_tokens=50, cache_creation_input_tokens=25)
        dumped = u.model_dump()
        restored = Usage(**dumped)
        assert restored.cache_creation_input_tokens == 25


# ── Task Model ───────────────────────────────────────────────────────

class TestTaskModelIntegration:
    def test_task_roundtrip(self) -> None:
        task = Task(
            id="1",
            subject="Build feature",
            description="Implement the new feature",
            status="in_progress",
            active_form="Building feature",
            blocks=["2"],
            blocked_by=[],
            metadata={"priority": "high"},
        )
        dumped = task.model_dump()
        restored = Task(**dumped)
        assert restored.id == "1"
        assert restored.metadata == {"priority": "high"}
        assert "2" in restored.blocks


# ── MCP String Utils ─────────────────────────────────────────────────

class TestMcpStringUtilsIntegration:
    def test_tool_name_format(self) -> None:
        from agent_butler.services.mcp.string_utils import is_mcp_tool_name, mcp_tool_name, parse_mcp_tool_name

        name = mcp_tool_name("github", "create_issue")
        assert name == "mcp__github__create_issue"
        assert is_mcp_tool_name(name) is True
        assert is_mcp_tool_name("Bash") is False

        parsed = parse_mcp_tool_name(name)
        assert parsed is not None
        assert parsed["serverName"] == "github"
        assert parsed["toolName"] == "create_issue"


# ── Settings File Reader ─────────────────────────────────────────────

class TestSettingsReaderIntegration:
    def test_read_valid_json(self, tmp_path: Path) -> None:
        from agent_butler.utils.settings import read_json_settings_file

        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"allow": ["Read"], "deny": []}))

        result = read_json_settings_file(str(settings_file))
        assert result.raw is not None
        assert result.raw["allow"] == ["Read"]
        assert result.parse_error is None

    def test_read_missing_file(self, tmp_path: Path) -> None:
        from agent_butler.utils.settings import read_json_settings_file

        result = read_json_settings_file(str(tmp_path / "nonexistent.json"))
        assert result.raw is None
        assert result.parse_error is None

    def test_read_invalid_json(self, tmp_path: Path) -> None:
        from agent_butler.utils.settings import read_json_settings_file

        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json")

        result = read_json_settings_file(str(bad_file))
        assert result.raw is None
        assert result.parse_error is not None
        assert "Invalid JSON" in result.parse_error


# ── Stream Debug ─────────────────────────────────────────────────────

class TestStreamDebugIntegration:
    def test_debug_disabled_by_default(self) -> None:
        from agent_butler.utils.stream_debug import is_stream_debug_enabled, write_stream_debug

        assert is_stream_debug_enabled() is False
        # Should not raise even when disabled
        write_stream_debug("test", {"key": "value"})


# ── Task Output ──────────────────────────────────────────────────────

class TestTaskOutputIntegration:
    @pytest.mark.asyncio
    async def test_output_file_lifecycle(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent_butler.utils.paths.get_projects_root", lambda: str(tmp_path / "projects"))

        from agent_butler.utils.task_output import (
            append_task_output,
            ensure_task_output_file,
            get_task_output_path,
            preview_tool_result,
        )

        file_path = await ensure_task_output_file("session-1", "agent-1")
        assert Path(file_path).exists()

        await append_task_output(file_path, {"type": "text", "text": "hello"})
        content = Path(file_path).read_text()
        assert "hello" in content

        # Preview truncation
        long_text = "x" * 5000
        preview = preview_tool_result(long_text, max_len=100)
        assert "truncated" in preview


# ── Memory Types ─────────────────────────────────────────────────────

class TestMemoryTypesIntegration:
    def test_is_memory_type(self) -> None:
        from agent_butler.context.memory.memory_types import MEMORY_TYPES, is_memory_type

        for t in MEMORY_TYPES:
            assert is_memory_type(t) is True
        assert is_memory_type("invalid") is False


# ── Conditional Skills ───────────────────────────────────────────────

class TestConditionalSkillsIntegration:
    def test_extract_tool_file_paths(self) -> None:
        from agent_butler.services.skills.conditional import extract_tool_file_paths

        paths = extract_tool_file_paths("Read", {"file_path": "/tmp/test.py"})
        assert "/tmp/test.py" in paths

        paths = extract_tool_file_paths("Glob", {"path": "/src"})
        assert "/src" in paths

        paths = extract_tool_file_paths("Bash", {"command": "ls"})
        assert paths == []


# ── CLI Bootstrap ────────────────────────────────────────────────────

class TestCliIntegration:
    def test_parse_args_defaults(self) -> None:
        from agent_butler.cli import _parse_args

        # Simulate no args
        import sys
        old_argv = sys.argv
        sys.argv = ["agent-butler"]
        try:
            args = _parse_args()
            assert args.model == os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
            assert args.plan is False
            assert args.auto is False
            assert args.print_mode is False
        finally:
            sys.argv = old_argv

    def test_parse_args_plan_mode(self) -> None:
        from agent_butler.cli import _determine_permission_mode

        class FakeArgs:
            plan = True
            auto = False

        assert _determine_permission_mode(FakeArgs()) == "plan"

        class FakeArgs2:
            plan = False
            auto = True

        assert _determine_permission_mode(FakeArgs2()) == "auto"

        class FakeArgs3:
            plan = False
            auto = False

        assert _determine_permission_mode(FakeArgs3()) is None


# ── Skill Budget ─────────────────────────────────────────────────────

class TestSkillBudgetIntegration:
    def test_format_within_budget(self) -> None:
        from agent_butler.services.skills.budget import format_skills_within_budget

        skills = [
            Skill(
                name=f"skill-{i}",
                description=f"Description for skill {i}",
                body="",
                file_path=f"/tmp/{i}/SKILL.md",
                base_dir=f"/tmp/{i}",
                source="user",
                frontmatter=SkillFrontmatter(allowed_tools=[]),
            )
            for i in range(5)
        ]

        result = format_skills_within_budget(skills, budget=10000)
        assert "skill-0" in result
        assert "skill-4" in result

        # Tight budget — should fall back to names only
        tight = format_skills_within_budget(skills, budget=50)
        assert "skill-0" in tight
