from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel


class McpStdioServerConfig(BaseModel):
    type: Literal["stdio"] | None = "stdio"
    command: str
    args: list[str] | None = None
    env: dict[str, str] | None = None


class McpHTTPServerConfig(BaseModel):
    type: Literal["http"] = "http"
    url: str
    headers: dict[str, str] | None = None


class McpSSEServerConfig(BaseModel):
    type: Literal["sse"] = "sse"
    url: str
    headers: dict[str, str] | None = None


McpServerConfig = Union[McpStdioServerConfig, McpHTTPServerConfig, McpSSEServerConfig]


class McpJsonConfig(BaseModel):
    mcp_servers: dict[str, McpServerConfig]


class ScopedMcpServerConfig(BaseModel):
    config: McpServerConfig
    scope: Literal["user", "project"]


class ConnectedMcpServer(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    name: str
    type: Literal["connected"] = "connected"
    client: Any
    capabilities: dict[str, Any] | None = None
    server_info: dict[str, str] | None = None
    config: ScopedMcpServerConfig
    cleanup: Any


class FailedMcpServer(BaseModel):
    name: str
    type: Literal["failed"] = "failed"
    config: ScopedMcpServerConfig
    error: str


class DisabledMcpServer(BaseModel):
    name: str
    type: Literal["disabled"] = "disabled"
    config: ScopedMcpServerConfig


class PendingMcpServer(BaseModel):
    name: str
    type: Literal["pending"] = "pending"
    config: ScopedMcpServerConfig
    started_at: float


McpServerConnection = Union[
    ConnectedMcpServer,
    FailedMcpServer,
    DisabledMcpServer,
    PendingMcpServer,
]
