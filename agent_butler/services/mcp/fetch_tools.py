from __future__ import annotations

from typing import Any

from ...tools.base import Tool
from ...types.mcp import ConnectedMcpServer
from ...types.tool import ToolContext, ToolResult
from ...utils.log import debug_log, log_warn
from .string_utils import mcp_tool_name

MAX_MCP_DESCRIPTION_LENGTH = 2048


def _stringify_mcp_content(content: Any) -> str:
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            block_type = block.get("type", "")
            if block_type == "text":
                parts.append(block.get("text", ""))
            elif block_type == "image":
                mime = block.get("mimeType", "?")
                data_len = len(block.get("data", ""))
                parts.append(f"[image: {mime}, {data_len} base64 chars]")
            elif block_type == "resource":
                r = block.get("resource", {})
                parts.append(r.get("text", f'[resource: {r.get("uri", "<no uri>")}]'))
            else:
                parts.append(f'[{block_type or "unknown"} block]')
        elif hasattr(block, "type"):
            if block.type == "text":
                parts.append(getattr(block, "text", ""))
            elif block.type == "image":
                mime = getattr(block, "mimeType", "?")
                data_len = len(getattr(block, "data", "") or "")
                parts.append(f"[image: {mime}, {data_len} base64 chars]")
            elif block.type == "resource":
                r = getattr(block, "resource", {})
                uri = getattr(r, "uri", "<no uri>") if hasattr(r, "uri") else "<no uri>"
                text = getattr(r, "text", None) if hasattr(r, "text") else None
                parts.append(text or f"[resource: {uri}]")
            else:
                parts.append(f"[{getattr(block, 'type', 'unknown')} block]")
    return "\n".join(parts)


def _truncate_description(desc: str | None) -> str:
    if not desc:
        return ""
    if len(desc) <= MAX_MCP_DESCRIPTION_LENGTH:
        return desc
    return desc[:MAX_MCP_DESCRIPTION_LENGTH] + "… [truncated]"


class _McpToolAdapter(Tool):
    def __init__(
        self,
        connection: ConnectedMcpServer,
        tool_name: str,
        description: str,
        input_schema: dict[str, Any],
        is_read_only_hint: bool,
    ) -> None:
        self._connection = connection
        self._tool_name = tool_name
        self._full_name = mcp_tool_name(connection.name, tool_name)
        self._description = description
        self._input_schema = input_schema
        self._is_read_only_hint = is_read_only_hint

    @property
    def name(self) -> str:
        return self._full_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        return self._input_schema

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        try:
            client = self._connection.client
            result = await client.call_tool(self._tool_name, input_data)
            content = _stringify_mcp_content(result.content if hasattr(result, "content") else result)
            return ToolResult(
                content=content,
                is_error=getattr(result, "isError", False),
            )
        except Exception as exc:
            return ToolResult(
                content=f"MCP tool '{self._full_name}' failed: {exc}",
                is_error=True,
            )

    def is_read_only(self) -> bool:
        return self._is_read_only_hint

    def is_enabled(self) -> bool:
        return True


async def fetch_tools_for_connection(
    connection: ConnectedMcpServer,
) -> list[Tool]:
    capabilities = connection.capabilities
    if capabilities and not capabilities.get("tools"):
        debug_log("mcp", f"[{connection.name}] no 'tools' capability declared, skipping tools/list")
        return []

    try:
        client = connection.client
        result = await client.list_tools()
    except Exception as exc:
        log_warn(f"MCP server '{connection.name}' tools/list failed: {exc}")
        return []

    tools: list[Tool] = []
    raw_tools = result.tools if hasattr(result, "tools") else result
    for mcp_tool in raw_tools:
        try:
            tool_name = (
                mcp_tool.name if hasattr(mcp_tool, "name")
                else mcp_tool.get("name", "")
            )
            desc = (
                mcp_tool.description if hasattr(mcp_tool, "description")
                else mcp_tool.get("description", "")
            )
            default_schema = {"type": "object", "properties": {}}
            schema = (
                mcp_tool.inputSchema if hasattr(mcp_tool, "inputSchema")
                else mcp_tool.get("inputSchema", default_schema)
            )
            annotations = (
                mcp_tool.annotations if hasattr(mcp_tool, "annotations")
                else mcp_tool.get("annotations", None)
            )
            is_read_only = False
            if annotations:
                is_read_only = getattr(annotations, "readOnlyHint", False) or (
                    annotations.get("readOnlyHint", False) if isinstance(annotations, dict) else False
                )

            adapter = _McpToolAdapter(
                connection=connection,
                tool_name=tool_name,
                description=_truncate_description(desc),
                input_schema=schema if isinstance(schema, dict) else {"type": "object", "properties": {}},
                is_read_only_hint=is_read_only,
            )
            tools.append(adapter)
        except Exception as exc:
            log_warn(
                f"MCP tool '{connection.name}.{getattr(mcp_tool, 'name', '?')}' "
                f"failed schema adaptation: {exc}"
            )

    debug_log("mcp", f"[{connection.name}] discovered {len(tools)} tool(s)")
    return tools


async def fetch_mcp_tools(client: Any) -> list[Tool]:
    try:
        result = await client.list_tools()
        raw_tools = result.tools if hasattr(result, "tools") else result
        return list(raw_tools)
    except Exception as exc:
        log_warn(f"fetch_mcp_tools failed: {exc}")
        return []
