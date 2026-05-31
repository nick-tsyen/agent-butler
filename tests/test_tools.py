from __future__ import annotations

from typing import Any

from agent_butler.tools.base import Tool, tool_to_api_param
from agent_butler.tools.registry import (
    clear_mcp_tools,
    find_tool_by_name,
    get_all_tools,
    get_tools_api_params,
    register_builtin_tools,
    register_mcp_tools,
)
from agent_butler.types.tool import ToolContext, ToolResult


class _MockTool(Tool):
    def __init__(
        self,
        tool_name: str = "MockTool",
        read_only: bool = True,
        enabled: bool = True,
    ) -> None:
        self._name = tool_name
        self._read_only = read_only
        self._enabled = enabled

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock tool {self._name}"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(content="ok")

    def is_read_only(self) -> bool:
        return self._read_only

    def is_enabled(self) -> bool:
        return self._enabled


class TestToolRegistry:
    def setup_method(self) -> None:
        clear_mcp_tools()

    def test_register_and_get_builtin_tools(self) -> None:
        tools = [_MockTool("A"), _MockTool("B")]
        register_builtin_tools(tools)
        result = get_all_tools()
        assert len(result) >= 2
        names = [t.name for t in result]
        assert "A" in names
        assert "B" in names

    def test_register_mcp_tools(self) -> None:
        mcp_tools = [_MockTool("mcp__server__tool1")]
        register_mcp_tools(mcp_tools)
        result = get_all_tools()
        names = [t.name for t in result]
        assert "mcp__server__tool1" in names

    def test_clear_mcp_tools(self) -> None:
        register_mcp_tools([_MockTool("mcp__test__x")])
        clear_mcp_tools()
        result = get_all_tools()
        names = [t.name for t in result]
        assert "mcp__test__x" not in names

    def test_find_tool_by_name(self) -> None:
        register_builtin_tools([_MockTool("FindMe")])
        found = find_tool_by_name("FindMe")
        assert found is not None
        assert found.name == "FindMe"

    def test_find_tool_by_name_not_found(self) -> None:
        found = find_tool_by_name("NonExistentTool_XYZ")
        assert found is None

    def test_disabled_tools_excluded(self) -> None:
        register_builtin_tools([_MockTool("Disabled", enabled=False)])
        result = get_all_tools()
        names = [t.name for t in result]
        assert "Disabled" not in names

    def test_get_tools_api_params(self) -> None:
        register_builtin_tools([_MockTool("EnterPlanMode"), _MockTool("Read")])
        params = get_tools_api_params(mode="plan")
        names = [p["name"] for p in params]
        assert "Read" in names
        assert "EnterPlanMode" not in names


class TestToolToApiParam:
    def test_basic_conversion(self) -> None:
        tool = _MockTool("TestConvert")
        param = tool_to_api_param(tool)
        assert param["name"] == "TestConvert"
        assert param["description"] == "Mock tool TestConvert"
        assert param["input_schema"] == {"type": "object", "properties": {}}
