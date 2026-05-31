---
title: "Testing: Structure & Coverage"
slide: "25"
section: "Testing & Development"
date: "2026-05-31"
---

# Testing: Structure & Coverage

## How to Run

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run full suite
pytest tests/ -v

# Run a specific module
pytest tests/test_permissions.py -v
```

## Five Test Modules

| Module | What it covers |
|--------|---------------|
| `test_tools.py` | Tool registry operations; `get_all_tools()`, `find_tool_by_name()`; tool execution contracts; read-only and concurrency-safe flags |
| `test_streaming.py` | `StreamEvent` accumulation; partial JSON assembly for `tool_use` blocks; SSE event parsing edge cases |
| `test_tasks.py` | `Task` and `TaskStatus` Pydantic model serialisation; field validation; status transitions |
| `test_permissions.py` | Rule matching (exact, wildcard, parameterised); mode transitions (`default` -> `plan` -> `auto`); plan mode hard-block behaviour |
| `test_sandbox.py` | SBPL profile compilation; compound command splitting (`&&`/`\|\|`); `should_use` gate logic |

## Shared Fixtures (`tests/conftest.py`)

- Mock `ToolContext` with stub callbacks
- Temporary directories for file-based operations
- Fake API response builders

## Scope

Note: integration tests (actual Anthropic API calls, live MCP connections) are not included — all tests are offline unit-level.

---

*Speaker notes: The test suite covers the trickiest parts of the system: streaming accumulation edge cases, permission rule matching, and sandbox profile generation. These are the areas most likely to have subtle bugs. Integration tests would require live API credentials and are left to the user.*
