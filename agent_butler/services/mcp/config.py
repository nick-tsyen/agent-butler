from __future__ import annotations

from typing import Any

from ...types.mcp import (
    McpHTTPServerConfig,
    McpServerConfig,
    McpSSEServerConfig,
    McpStdioServerConfig,
    ScopedMcpServerConfig,
)
from ...utils.log import log_warn
from ...utils.paths import get_settings_paths
from ...utils.settings import read_json_settings_file


class McpConfigLoadResult:
    def __init__(
        self,
        servers: dict[str, ScopedMcpServerConfig],
        errors: list[str],
    ) -> None:
        self.servers = servers
        self.errors = errors


def _validate_server_config(
    name: str,
    raw: Any,
    scope: str,
) -> tuple[McpServerConfig | None, str | None]:
    if not isinstance(raw, dict):
        return None, f"mcpServers.{name} must be an object"

    server_type = raw.get("type")

    if server_type is not None and server_type not in ("stdio", "http", "sse"):
        return None, (
            f"mcpServers.{name} ({scope}): unsupported transport '{server_type}'. "
            "Use 'stdio', 'http', or 'sse'."
        )

    if server_type in ("http", "sse"):
        return _validate_remote_config(name, raw, scope, server_type)
    return _validate_stdio_config(name, raw, scope)


def _validate_stdio_config(
    name: str,
    obj: dict[str, Any],
    scope: str,
) -> tuple[McpStdioServerConfig | None, str | None]:
    command = obj.get("command")
    if not isinstance(command, str) or not command.strip():
        return None, f"mcpServers.{name} ({scope}): 'command' is required and must be a non-empty string"

    args = obj.get("args")
    if args is not None:
        if not isinstance(args, list):
            return None, f"mcpServers.{name} ({scope}): 'args' must be an array of strings"
        if any(not isinstance(a, str) for a in args):
            return None, f"mcpServers.{name} ({scope}): 'args' must contain only strings"

    env = obj.get("env")
    if env is not None:
        if not isinstance(env, dict):
            return None, f"mcpServers.{name} ({scope}): 'env' must be a string→string map"
        for k, v in env.items():
            if not isinstance(v, str):
                return None, f"mcpServers.{name} ({scope}): env.{k} must be a string"

    return McpStdioServerConfig(
        type="stdio",
        command=command,
        args=args if isinstance(args, list) else [],
        env=env if isinstance(env, dict) else None,
    ), None


def _validate_remote_config(
    name: str,
    obj: dict[str, Any],
    scope: str,
    server_type: str,
) -> tuple[McpServerConfig | None, str | None]:
    url = obj.get("url")
    if not isinstance(url, str) or not url.strip():
        return None, f"mcpServers.{name} ({scope}): '{server_type}' transport requires 'url'"

    from urllib.parse import urlparse

    try:
        urlparse(url)
    except Exception:
        return None, f"mcpServers.{name} ({scope}): 'url' is not a valid URL: {url}"

    headers = obj.get("headers")
    if headers is not None:
        if not isinstance(headers, dict):
            return None, f"mcpServers.{name} ({scope}): 'headers' must be a string→string map"
        for k, v in headers.items():
            if not isinstance(v, str):
                return None, f"mcpServers.{name} ({scope}): headers.{k} must be a string"

    if server_type == "http":
        return McpHTTPServerConfig(
            type="http",
            url=url,
            headers=headers if isinstance(headers, dict) else None,
        ), None
    else:
        return McpSSEServerConfig(
            type="sse",
            url=url,
            headers=headers if isinstance(headers, dict) else None,
        ), None


def _extract_scoped_servers(
    raw: Any,
    scope: str,
    file_path: str,
    errors: list[str],
) -> dict[str, ScopedMcpServerConfig]:
    if not isinstance(raw, dict):
        return {}
    mcp_servers = raw.get("mcpServers")
    if mcp_servers is None:
        return {}
    if not isinstance(mcp_servers, dict):
        errors.append(f"{file_path}: 'mcpServers' must be an object")
        return {}

    out: dict[str, ScopedMcpServerConfig] = {}
    for server_name, raw_config in mcp_servers.items():
        config, err = _validate_server_config(server_name, raw_config, scope)
        if err:
            errors.append(err)
            continue
        if config is not None:
            out[server_name] = ScopedMcpServerConfig(config=config, scope=scope)
    return out


def load_mcp_config(cwd: str) -> dict[str, ScopedMcpServerConfig]:
    result = load_mcp_configs(cwd)
    for err in result.errors:
        log_warn(f"[mcp] config: {err}")
    return result.servers


def load_mcp_configs(cwd: str) -> McpConfigLoadResult:
    paths = get_settings_paths(cwd)
    errors: list[str] = []

    user_file = read_json_settings_file(paths["user"])
    project_file = read_json_settings_file(paths["project"])

    if user_file.parse_error:
        errors.append(user_file.parse_error)
    if project_file.parse_error:
        errors.append(project_file.parse_error)

    user_servers = _extract_scoped_servers(
        user_file.raw, "user", paths["user"], errors,
    )
    project_servers = _extract_scoped_servers(
        project_file.raw, "project", paths["project"], errors,
    )

    servers = {**user_servers, **project_servers}
    return McpConfigLoadResult(servers=servers, errors=errors)
