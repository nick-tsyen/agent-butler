from __future__ import annotations

from typing import Any

import pytest

from agent_butler.permissions.permissions import (
    PermissionSettings,
    build_permission_rule_hint,
    check_permission,
    matches_permission_rule,
    summarize_permission_request,
)
from agent_butler.tools.base import Tool
from agent_butler.types.tool import ToolContext, ToolResult


class _MockReadTool(Tool):
    @property
    def name(self) -> str:
        return "Read"

    @property
    def description(self) -> str:
        return "Read a file"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(content="file content")

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True


class _MockWriteTool(Tool):
    @property
    def name(self) -> str:
        return "Write"

    @property
    def description(self) -> str:
        return "Write a file"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(content="written")

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


class _MockBashTool(Tool):
    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return "Run a shell command"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(content="done")

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


class TestMatchesPermissionRule:
    def test_exact_tool_name_match(self) -> None:
        assert matches_permission_rule("Write", "Write", {}) is True

    def test_exact_tool_name_no_match(self) -> None:
        assert matches_permission_rule("Read", "Write", {}) is False

    def test_bash_rule_match(self) -> None:
        assert matches_permission_rule("Bash(npm *)", "Bash", {"command": "npm install"}) is True

    def test_bash_rule_no_match(self) -> None:
        assert matches_permission_rule("Bash(rm *)", "Bash", {"command": "npm install"}) is False

    def test_skill_rule_match(self) -> None:
        assert matches_permission_rule("Skill(review)", "Skill", {"skill": "review"}) is True

    def test_skill_rule_wildcard(self) -> None:
        assert matches_permission_rule("Skill(test-*)", "Skill", {"skill": "test-review"}) is True

    def test_empty_rule(self) -> None:
        assert matches_permission_rule("", "Write", {}) is False

    def test_mcp_wildcard_rule(self) -> None:
        assert matches_permission_rule("mcp__server__*", "mcp__server__tool1", {}) is True


class TestSummarizePermissionRequest:
    def test_bash_summary(self) -> None:
        summary = summarize_permission_request("Bash", {"command": "npm install"})
        assert "npm install" in summary

    def test_generic_summary(self) -> None:
        summary = summarize_permission_request("Write", {"file_path": "/tmp/test.txt"})
        assert "file_path" in summary


class TestBuildPermissionRuleHint:
    def test_bash_hint(self) -> None:
        hint = build_permission_rule_hint("Bash", {"command": "npm install --save"})
        assert "Bash(npm" in hint

    def test_skill_hint(self) -> None:
        hint = build_permission_rule_hint("Skill", {"skill": "review"})
        assert "Skill(review)" == hint

    def test_generic_hint(self) -> None:
        hint = build_permission_rule_hint("Write", {})
        assert hint == "Write"


class TestCheckPermission:
    @pytest.mark.asyncio
    async def test_read_tool_auto_allowed(self) -> None:
        tool = _MockReadTool()
        response = await check_permission(
            tool,
            {"file_path": "/tmp/test.txt"},
            "/tmp",
            mode="default",
            settings=PermissionSettings(),
        )
        assert response.behavior == "allow"

    @pytest.mark.asyncio
    async def test_auto_mode_allows_all(self) -> None:
        tool = _MockWriteTool()
        response = await check_permission(
            tool,
            {"file_path": "/tmp/test.txt"},
            "/tmp",
            mode="auto",
            settings=PermissionSettings(),
        )
        assert response.behavior == "allow"

    @pytest.mark.asyncio
    async def test_plan_mode_blocks_write(self) -> None:
        tool = _MockWriteTool()
        response = await check_permission(
            tool,
            {"file_path": "/tmp/test.txt"},
            "/tmp",
            mode="plan",
            settings=PermissionSettings(),
        )
        assert response.behavior == "deny"

    @pytest.mark.asyncio
    async def test_plan_mode_allows_read(self) -> None:
        tool = _MockReadTool()
        response = await check_permission(
            tool,
            {"file_path": "/tmp/test.txt"},
            "/tmp",
            mode="plan",
            settings=PermissionSettings(),
        )
        assert response.behavior == "allow"

    @pytest.mark.asyncio
    async def test_deny_rule_blocks(self) -> None:
        tool = _MockWriteTool()
        settings = PermissionSettings(deny=["Write"])
        response = await check_permission(
            tool,
            {"file_path": "/tmp/test.txt"},
            "/tmp",
            mode="default",
            settings=settings,
        )
        assert response.behavior == "deny"

    @pytest.mark.asyncio
    async def test_allow_rule_permits(self) -> None:
        tool = _MockWriteTool()
        settings = PermissionSettings(allow=["Write"])
        response = await check_permission(
            tool,
            {"file_path": "/tmp/test.txt"},
            "/tmp",
            mode="default",
            settings=settings,
        )
        assert response.behavior == "allow"
