---
title: "Design Patterns & Key Takeaways"
slide: "27"
section: "Wrap-up"
date: "2026-05-31"
---

# Design Patterns & Key Takeaways

## 1. Async-first

`asyncio` is the threading model throughout — no threads, all I/O is non-blocking. `asyncio.gather()` enables real parallelism for safe tool batches.

## 2. Pydantic for every boundary

All messages, tool results, tasks, skills, and agent definitions are `BaseModel` subclasses — validated at entry, serialisable to JSON at exit.

## 3. Layered separation of concerns

Five layers, each with one job. The UI layer never calls the API; the core loop never renders. Communication is always downward via async generators.

## 4. Generator-based streaming

The API layer, core loop, session controller, and UI layer all communicate via `AsyncGenerator`. No shared mutable state between layers — just a typed stream of events.

## 5. Multi-source config hierarchy

User -> project -> session. Later entries override earlier ones. Predictable override semantics with no magic.

## 6. Everything is a tool / skill / agent

New capabilities are added by implementing `Tool`, dropping a `.md`, or adding a `.json`. The core is closed to modification; extensions are open.

## 7. Minimal blast radius

`is_concurrency_safe()`, `is_read_only()`, permission modes, sandbox profiles, and `max_turns` all independently limit the scope of any single operation. Defence in depth.

---

*Speaker notes: These seven patterns are the design vocabulary of Easy Agent. When in doubt about where to put new code or how to extend the system, check which pattern applies. The generator-based streaming pattern in particular is what makes the system composable — each layer can be tested independently.*
