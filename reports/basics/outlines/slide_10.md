---
title: "Tool Execution: Batching Strategy"
slide: "10"
section: "Core Agentic Loop"
date: "2026-05-31"
---

# Tool Execution: Batching Strategy

**The problem:** Claude often calls multiple tools in one turn (e.g., read 5 files). Running them sequentially wastes time. But not all tools are safe to run in parallel.

**Solution:** `is_concurrency_safe()` method on `Tool` determines grouping.

---

**Two-group execution model**

| Batch | Tools | Mechanism |
|-------|-------|-----------|
| Concurrent (safe) | Read, Grep, Glob, Agent | `asyncio.gather()` |
| Sequential (unsafe) | Write, Edit, Bash, Skill, TaskCreate, TaskUpdate, TaskGet, TaskList, EnterPlanMode, ExitPlanMode, MemoryWrite | `await` one by one |

Execution order within a turn: all concurrent tools run first (in parallel), then sequential tools run one by one.

---

**Example scenario**

```
Claude's turn calls: [Read(a.py), Read(b.py), Read(c.py), Write(d.py)]
→ Concurrent batch: [Read(a.py), Read(b.py), Read(c.py)]  ← parallel
→ Sequential batch: [Write(d.py)]                          ← after concurrent completes
```

**Real-world benefit:** reading 10 files takes the time of reading 1 file.

---

*Speaker notes: The batching logic lives in agentic_loop.py. The `is_concurrency_safe()` method can also inspect `input_data` — so in theory a tool could decide safety per invocation. Currently all reads return True unconditionally.*
