# # Step-by-step Agentic System Building

Each file is a self-contained, progressively more capable slice of a terminal coding agent — starting from a raw streaming API call and ending with Git-worktree-isolated background agents.

## Steps

| File                  | What it covers                                                                               |
| --------------------- | -------------------------------------------------------------------------------------------- |
| [step1.py](./step1.py)   | `AsyncAnthropic` streaming client; text and tool-use events yielded via async generator    |
| [step2.py](./step2.py)   | Interactive REPL using `asyncio` + `run_in_executor` for non-blocking input              |
| [step3.py](./step3.py)   | `Tool` Protocol + `ReadTool` with `aiofiles` and `pathlib.Path` workspace sandboxing |
| [step4.py](./step4.py)   | Agentic loop: stream → tool execution → stream;`query_done` event carries final result   |
| [step5.py](./step5.py)   | All 6 core tools: Read / Write / Edit / Grep / Glob / Bash                                   |
| [step6.py](./step6.py)   | Dynamic system prompt assembly with concurrent git status + AGENT.md reads                   |
| [step7.py](./step7.py)   | Permission model: allow / ask / deny with dangerous command detection                        |
| [step8.py](./step8.py)   | `QueryEngine` class with slash-command handling and cumulative token tracking              |
| [step9.py](./step9.py)   | JSONL session persistence, restore from disk, and project history listing                    |
| [step10.py](./step10.py) | File-based long-term memory with MEMORY.md index and relevance search                        |
| [step11.py](./step11.py) | Token estimation, micro-compact (zero API cost), and AI-powered full compaction              |
| [step12.py](./step12.py) | Token budget management: 4-state warnings, circuit breaker, result truncation, output tiers  |
| [step13.py](./step13.py) | Plan mode with `EnterPlanMode` / `ExitPlanMode` tools                                    |
| [step14.py](./step14.py) | `TodoWrite` tool with in-memory session store and change listeners                         |
| [step15.py](./step15.py) | Persistent task graph with CRUD, stable numeric IDs, and dependency edges                    |
| [step16.py](./step16.py) | MCP client: config validation, transport factories (stdio / http / sse), tool adapter        |
| [step17.py](./step17.py) | Skills system: file discovery, registry,`UseSkill` / `ListSkills` tools                  |
| [step18.py](./step18.py) | Bash sandboxing: policy enforcement, session allow-rules, optional Docker wrapping           |
| [step19.py](./step19.py) | Sub-agents via `Task` tool with isolated child context and tool executor                   |
| [step20.py](./step20.py) | Background agents in Git worktrees with async farm, semaphore, and fire-and-forget           |

## Design notes

- **Async generators** yield a final `message_done` / `query_done` event carrying the assembled result — Python prohibits `return <value>` inside an async generator, so the result is embedded in the last event instead.
- **`asyncio.create_subprocess_exec`** is used in place of Node's `child_process`.
- **`aiofiles`** handles all async file I/O.
- **`pathlib.Path`** is used for path operations throughout.
- **Relative imports** (`from .step1 import …`) wire dependent steps together.
- Files are standalone enough to read individually; each module docstring restates the step's goal.
