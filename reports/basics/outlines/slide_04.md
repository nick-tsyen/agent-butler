---
title: "Five-Layer Architecture"
slide: "04"
section: "High-Level Architecture"
date: "2026-05-31"
---

# Architecture: Five Layers

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 1: Interaction                                        │
│  Rich console · prompt_toolkit input · Live TUI updates      │
│  ui/app.py · ui/layout.py · ui/input_prompt.py              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  Layer 2: Orchestration                                      │
│  SessionController · multi-turn flow · command dispatch      │
│  ui/session_hook.py                                          │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  Layer 3: Core Agentic Loop                                  │
│  Reason → Act → Observe · up to 100 turns                   │
│  core/agentic_loop.py · core/query_engine.py                │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  Layer 4: Tooling                                            │
│  File ops · shell · search · delegation · skills · MCP      │
│  tools/ · services/skills/ · services/mcp/                  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  Layer 5: Model Communication                                │
│  Anthropic SDK streaming · retry · JSON accumulation        │
│  services/api/streaming.py · services/api/client.py         │
└──────────────────────────────────────────────────────────────┘
```

**Rule:** each layer communicates only downward. The UI never calls the API directly; the core loop never renders to the terminal.

---

*Speaker notes: This layering is the main architectural constraint that keeps the codebase maintainable. UI concerns stay out of the agentic loop, and model communication concerns stay out of tool execution. Each layer has a single, well-defined responsibility, which makes it straightforward to test or replace individual layers without cascading changes.*
