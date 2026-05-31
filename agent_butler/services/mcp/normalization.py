from __future__ import annotations

import re
from typing import Any


def normalize_name_for_mcp(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def normalize_mcp_tool(server_name: str, tool: dict[str, Any]) -> dict[str, Any]:
    from .string_utils import mcp_tool_name

    raw_name = tool.get("name", "") if isinstance(tool, dict) else getattr(tool, "name", "")
    raw_desc = tool.get("description", "") if isinstance(tool, dict) else getattr(tool, "description", "")
    default_schema = {"type": "object", "properties": {}}
    raw_schema = (
        tool.get("inputSchema", default_schema) if isinstance(tool, dict)
        else getattr(tool, "inputSchema", default_schema)
    )
    raw_annotations = (
        tool.get("annotations") if isinstance(tool, dict)
        else getattr(tool, "annotations", None)
    )

    full_name = mcp_tool_name(server_name, raw_name)
    desc = raw_desc[:2048] + "… [truncated]" if len(raw_desc) > 2048 else raw_desc

    is_read_only = False
    if raw_annotations:
        is_read_only = (
            raw_annotations.get("readOnlyHint", False)
            if isinstance(raw_annotations, dict)
            else getattr(raw_annotations, "readOnlyHint", False)
        )

    return {
        "name": full_name,
        "description": desc,
        "input_schema": raw_schema if isinstance(raw_schema, dict) else {"type": "object", "properties": {}},
        "is_read_only": is_read_only,
        "original_name": raw_name,
    }
