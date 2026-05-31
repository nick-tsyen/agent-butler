---
title: "Streaming: SSE Event Accumulation"
slide: "12"
section: "API & Streaming Layer"
date: "2026-05-31"
---

# Streaming: SSE Event Accumulation

**Core function**

```python
# services/api/streaming.py
async def stream_message(
    params: StreamRequestParams
) -> AsyncGenerator[StreamEvent, StreamResult]:
    async with client.messages.stream(...) as stream:
        async for event in stream:
            yield transform(event)
```

---

**Why per-index JSON accumulation is needed**

- Claude streams tool input JSON in fragments across multiple SSE events
- Each fragment has an index (which tool call it belongs to)
- Must accumulate per-index until `input_json_delta` events stop, then parse

---

**`StreamEvent` types emitted upstream**

| Event | Contains |
|-------|----------|
| `StreamMessageStartEvent` | Message ID |
| `StreamTextEvent` | Text delta string |
| `StreamThinkingEvent` | Thinking delta (extended thinking) |
| `StreamToolUseStartEvent` | Tool name + tool ID |
| `StreamToolUseInputEvent` | Partial JSON delta |
| `StreamMessageDoneEvent` | Final usage stats + stop reason |
| `StreamErrorEvent` | Error details |

---

**Cache metrics tracked in `StreamMessageDoneEvent`**

- `cache_creation_input_tokens` — tokens written to prompt cache
- `cache_read_input_tokens` — tokens served from cache (cheaper)

---

*Speaker notes: The per-index accumulation is the trickiest part of the streaming layer. It's why streaming.py is one of the more complex files despite being logically simple in purpose. The cache metrics matter for cost tracking.*
