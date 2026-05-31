---
title: "MCP: Model Context Protocol"
slide: "17"
section: "Extensions & Integrations"
date: "2026-05-31"
---

# MCP: Model Context Protocol

MCP (Model Context Protocol) is an open standard for exposing tool APIs to LLMs. A server announces its tools; the client discovers them and routes calls. Agent Butler implements the MCP client side, connecting to external servers over stdio, HTTP, or SSE transports.

---

**Configuration** (`~/.agent-butler/settings.json`)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/workspace"],
      "transport": "stdio"
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "transport": "stdio",
      "env": { "GITHUB_TOKEN": "..." }
    }
  }
}
```

---

**Bootstrap flow** (`services/mcp/bootstrap.py`)

```
settings.json
  -> parse mcpServers configs
       -> connect to each server (30s timeout)
            -> call list_tools()
                 -> get: name, description, input schema
                      -> wrap as native Tool object
                           -> name: mcp__<server>__<tool>
                                e.g. mcp__filesystem__read_file
                                     -> register in _mcp_tools global
```

---

**Key files**

| File | Responsibility |
|------|---------------|
| `services/mcp/bootstrap.py` | Orchestrates startup connection and registration |
| `services/mcp/client.py` | Connection caching keyed by config signature |
| `services/mcp/fetch_tools.py` | Calls `list_tools()` and wraps results |
| `services/mcp/normalization.py` | Normalises heterogeneous MCP schemas to internal format |

---

*Speaker notes: MCP is the extensibility escape hatch for external integrations. Any MCP-compatible tool server can be wired in with three lines of JSON. The `mcp__` prefix namespacing prevents collisions with built-in tools.*
