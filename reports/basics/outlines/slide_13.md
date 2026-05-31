---
title: "Retry Strategy & Token Budgets"
slide: "13"
section: "API & Streaming Layer"
date: "2026-05-31"
---

# Retry Strategy & Token Budgets

**The wrapper**

```python
# services/api/streaming.py
async def stream_message_with_retry(params):
    # First attempt: 8K max_tokens
    result = await stream_message(params.with_max_tokens(8192))
    
    if result.stop_reason == "max_tokens":
        # Escalate: retry with 64K
        result = await stream_message(params.with_max_tokens(65536))
    
    return result
```

---

**Token budget summary**

| Parameter | Default | Override |
|-----------|---------|----------|
| `max_tokens` (first attempt) | 8,192 | — |
| `max_tokens` (on truncation) | 65,536 | — |
| Context window ceiling | Model default | `CLAUDE_CODE_MAX_CONTEXT_TOKENS` env var |

---

**Auto-compaction** (`context/auto_compact.py`)

- **80% of context window** → emit warning to user
- **95% of context window** → trigger `compaction.py`: summarise conversation, replace history with summary
- Token estimation without API call: `utils/tokens.py` (181 lines of heuristic estimation)

---

**Cumulative tracking**

`SessionState` accumulates input + output + cache tokens across all turns for display in the status bar.

---

*Speaker notes: The two-tier max_tokens approach avoids paying for 64K on every call (which is expensive) while still handling cases where Claude's reasoning legitimately needs more space. Auto-compaction keeps long sessions usable.*
