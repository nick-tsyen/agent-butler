---
title: "Full Turn: Sequence Diagram"
slide: "11"
section: "Core Agentic Loop"
date: "2026-05-31"
---

# Full Turn: Sequence Diagram

```
User types input
  │
  ▼
App._handle_submit(text)
  │
  ▼
SessionController.submit(text)
  ├─ messages.append(UserMessage)
  └─ _run_agent_loop()
       │
       ▼
     query()  [async generator — core/agentic_loop.py]
       ├─ stream_message_with_retry()    ← Anthropic API call
       │    └─ yield text deltas        → UITextDelta events
       │
       ├─ extract ToolUseBlocks from response
       │
       ├─ for each tool:
       │    ├─ check_permission()
       │    │    └─ if needed: await on_permission_request
       │    │         └─ UI shows inline confirmation prompt
       │    └─ tool.call(input, context)
       │         └─ yield UIToolDone
       │
       ├─ messages.append(tool_results)
       └─ loop if stop_reason == "tool_use"
            │
            ▼ (otherwise)
          yield UITurnComplete
               │
               ▼
           App._process_event()
               └─ _layout.add_event()
                    └─ Rich Live.refresh()
```

---

**Source files involved**

`ui/app.py`, `ui/session_hook.py`, `core/agentic_loop.py`, `permissions/permissions.py`, `services/api/streaming.py`

---

*Speaker notes: The key insight is that everything flows through async generators. The agentic loop yields events; the session controller forwards them; the UI layer consumes them. No shared mutable state is needed between layers — just a stream of typed events.*
