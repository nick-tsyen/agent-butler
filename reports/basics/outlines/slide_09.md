---
title: "The Core Loop: Reason → Act → Observe"
slide: "09"
section: "Core Agentic Loop"
date: "2026-05-31"
---

# The Core Loop: Reason → Act → Observe

**Central function signature**

```python
# core/agentic_loop.py
async def query(
    messages: list[Message],
    tools: list[Tool],
    on_permission_request: Callable,
    abort_event: asyncio.Event,
    ...
) -> AsyncGenerator[dict[str, Any], None]:
```

---

**Loop pseudocode**

```
while turn_count < 100:
    # REASON: stream Claude's response
    stream Claude via stream_message_with_retry()
    accumulate text + tool_use blocks

    if stop_reason != "tool_use":
        yield final result
        break

    # ACT: partition and execute tools
    safe, unsafe = partition(tools, is_concurrency_safe)
    await asyncio.gather(*[run(t) for t in safe])
    for t in unsafe:
        await run(t)

    # OBSERVE: append results and loop
    messages.append(tool_results)
    turn_count += 1
```

---

**Yielded event types**

| Event type | When emitted |
|------------|--------------|
| `text` | Streaming text delta |
| `tool_use_start` | Tool card appears in UI |
| `tool_execution_done` | Tool results returned |
| `result` | Final message + usage stats |

---

*Speaker notes: The loop is a simple while-loop. The complexity is in the tool batching and permission checks, not the loop control itself. Max 100 turns prevents infinite loops from Claude getting stuck.*
