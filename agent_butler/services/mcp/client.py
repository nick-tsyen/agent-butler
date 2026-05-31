from __future__ import annotations

import asyncio
import os

from ...types.mcp import (
    ConnectedMcpServer,
    FailedMcpServer,
    McpServerConnection,
    ScopedMcpServerConfig,
)
from ...utils.log import debug_log, log_warn

CONNECT_TIMEOUT_MS = 30_000

_connection_cache: dict[str, asyncio.Future[McpServerConnection]] = {}
_active_connections: dict[str, ConnectedMcpServer] = {}


def _get_connect_timeout_ms() -> int:
    env = os.environ.get("MCP_CONNECT_TIMEOUT", "")
    try:
        val = int(env)
        return val if val > 0 else CONNECT_TIMEOUT_MS
    except (ValueError, TypeError):
        return CONNECT_TIMEOUT_MS


def _get_cache_key(name: str, config: ScopedMcpServerConfig) -> str:
    cfg = config.config
    cfg_type = getattr(cfg, "type", None) or "stdio"
    if cfg_type in ("http", "sse"):
        return f"{name}:{cfg_type}:{getattr(cfg, 'url', '')}:{getattr(cfg, 'headers', '')}"
    return f"{name}:stdio:{getattr(cfg, 'command', '')}:{getattr(cfg, 'args', '')}:{getattr(cfg, 'env', '')}"


async def connect_mcp_server(
    name: str,
    config: ScopedMcpServerConfig,
) -> McpServerConnection:
    key = _get_cache_key(name, config)
    if key in _connection_cache:
        return await _connection_cache[key]

    loop = asyncio.get_event_loop()
    future: asyncio.Future[McpServerConnection] = loop.create_future()
    _connection_cache[key] = future

    try:
        connection = await _do_connect(name, config)
        future.set_result(connection)
        if isinstance(connection, ConnectedMcpServer):
            _active_connections[name] = connection
        return connection
    except Exception as exc:
        failed = FailedMcpServer(
            name=name,
            type="failed",
            config=config,
            error=str(exc),
        )
        if not future.done():
            future.set_result(failed)
        return failed


async def _do_connect(
    name: str,
    config: ScopedMcpServerConfig,
) -> McpServerConnection:
    cfg = config.config
    cfg_type = getattr(cfg, "type", None) or "stdio"

    try:
        from mcp import ClientSession
        from mcp.client.stdio import StdioClientTransport
    except ImportError:
        return FailedMcpServer(
            name=name,
            type="failed",
            config=config,
            error="mcp package not installed. Install with: pip install 'mcp[cli]'",
        )

    timeout_ms = _get_connect_timeout_ms()

    try:
        if cfg_type == "stdio":
            transport = StdioClientTransport(
                command=cfg.command,
                args=cfg.args or [],
                env={**os.environ, **(cfg.env or {})},
            )
        else:
            return FailedMcpServer(
                name=name,
                type="failed",
                config=config,
                error=f"Transport type '{cfg_type}' not yet implemented (stdio only for now)",
            )
    except Exception as exc:
        log_warn(f"MCP server '{name}' failed to initialize transport: {exc}")
        return FailedMcpServer(
            name=name,
            type="failed",
            config=config,
            error=str(exc),
        )

    client = ClientSession()

    try:
        await asyncio.wait_for(
            client.connect(transport),
            timeout=timeout_ms / 1000,
        )
    except asyncio.TimeoutError:
        log_warn(f"MCP server '{name}' connection timed out after {timeout_ms}ms")
        try:
            await transport.close()
        except Exception:
            pass
        return FailedMcpServer(
            name=name,
            type="failed",
            config=config,
            error=f"Connection timed out after {timeout_ms}ms",
        )
    except Exception as exc:
        log_warn(f"MCP server '{name}' failed to connect: {exc}")
        try:
            await transport.close()
        except Exception:
            pass
        return FailedMcpServer(
            name=name,
            type="failed",
            config=config,
            error=str(exc),
        )

    capabilities = None
    server_info = None
    try:
        init_result = await client.initialize()
        if hasattr(init_result, "capabilities"):
            capabilities = init_result.capabilities
        if hasattr(init_result, "serverInfo"):
            info = init_result.serverInfo
            server_info = {
                "name": getattr(info, "name", name),
                "version": getattr(info, "version", "0.0.0"),
            }
    except Exception:
        pass

    debug_log("mcp", f"[{name}] connected via {cfg_type}")

    async def cleanup() -> None:
        _active_connections.pop(name, None)
        try:
            await client.close()
        except Exception:
            pass

    caps = None
    if capabilities and hasattr(capabilities, "model_dump"):
        caps = capabilities.model_dump()
    elif isinstance(capabilities, dict):
        caps = capabilities

    return ConnectedMcpServer(
        name=name,
        type="connected",
        client=client,
        capabilities=caps,
        server_info=server_info,
        config=config,
        cleanup=cleanup,
    )


async def clear_server_cache(name: str, config: ScopedMcpServerConfig) -> None:
    key = _get_cache_key(name, config)
    _connection_cache.pop(key, None)
    existing = _active_connections.pop(name, None)
    if existing and existing.cleanup:
        try:
            await existing.cleanup()
        except Exception:
            pass


async def disconnect_all() -> None:
    conns = list(_active_connections.values())
    _active_connections.clear()
    _connection_cache.clear()
    results = await asyncio.gather(
        *[c.cleanup() for c in conns if c.cleanup],
        return_exceptions=True,
    )
    for r in results:
        if isinstance(r, Exception):
            debug_log("mcp", f"disconnect_all error: {r}")


def get_active_connections() -> list[ConnectedMcpServer]:
    return list(_active_connections.values())
