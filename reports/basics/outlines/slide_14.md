---
title: "Tools: Abstract Base & Registry"
slide: "14"
section: "Tool System"
date: "2026-05-31"
---

# Tools: Abstract Base & Registry

**The base class**

```python
# tools/base.py
class Tool(ABC):
    @abstractmethod
    async def call(
        self,
        input_data: dict,
        context: ToolContext
    ) -> ToolResult: ...

    @abstractmethod
    def is_read_only(self) -> bool: ...

    def is_concurrency_safe(
        self, input_data: dict | None = None
    ) -> bool:
        return False  # default: sequential

    def is_enabled(self) -> bool:
        return True   # default: always on
```

---

**Supporting types**

```python
# types/tool.py
@dataclass
class ToolContext:
    messages: list[Message]
    abort_event: asyncio.Event
    on_permission_request: Callable
    session_id: str
    # ... other session state

@dataclass
class ToolResult:
    output: str
    is_error: bool = False
```

---

**The registry** (`tools/registry.py`)

- Two global lists: `_builtin_tools` and `_mcp_tools`
- `get_all_tools()` — filters by `is_enabled()`, returns combined list
- `find_tool_by_name(name: str) -> Tool | None` — used by the agentic loop to dispatch calls
- `register_builtin_tools(tools)` / `register_mcp_tools(tools)` — called at bootstrap

---

*Speaker notes: The Tool abstraction is intentionally minimal. The four methods are the only contract. Everything else — input schema, name, description — is handled by concrete subclasses and used by the system prompt assembler to generate tool definitions for Claude.*
