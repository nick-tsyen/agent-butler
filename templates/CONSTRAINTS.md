# Architectural Constraints

> If a rule cannot be mechanically broken in a build pipeline, it does not exist. Every constraint
> here must have a corresponding executable check (see `check_boundaries.py`). Agents copy whatever
> patterns already exist in the repo — even bad ones — so these boundaries must be established on
> **day one**, not once the codebase has grown.

## Layered Domain Architecture

Each domain is divided into fixed layers. **Dependencies flow strictly forward — a layer may only
import from layers below it.** Cross-domain concerns enter only through explicit `Providers`
interfaces; any other dependency is forbidden.

```
Types → Config → Repository → Service → Runtime → UI
```

- **Types / Models** — pure declarations, interfaces, schemas. **Zero dependencies.**
- **Config** — static env vars, feature flags, constants. Imports Types only; no execution logic.
- **Repository / Data Access** — talks to DBs, third-party APIs, the filesystem. Imports Config +
  Types; contains **zero business validation**.
- **Service / Domain Logic** — the brain: coordinates repositories, applies validation, transforms
  models. Agnostic of how it is invoked (UI, CLI, server).
- **Runtime** — wiring/composition for a given entry point.
- **UI / Presentation** — renders state, captures intent. **Calls the Service layer only.**

**The invariant:** a `Repository` may not import from `Service`; a `Config` may not import from
`UI`; the renderer may not touch the filesystem directly. If it does, the boundary is violated and
the build must fail.

## Principle: enforce invariants, don't micromanage

Require *outcomes* ("data is parsed at the boundary"), not *implementations* ("use library X"). Let
the source code carry type and config detail; this file carries only the boundaries that must hold.

## Agent-Oriented Error Messages (WHAT / WHY / FIX)

Every check that enforces a constraint must emit an error that an agent can act on without guessing.
Three elements, always:

```
WHAT: <what went wrong, with file:line>
WHY:  <which invariant it violates / why it matters>
FIX:  <the concrete corrective step to take>
```

Example:

```
ERROR: Found direct import of 'fs' in src/renderer/App.tsx:12
WHY:   The renderer layer must stay decoupled from OS operations (security/portability).
FIX:   Move file operations to src/preload/file-ops.ts and call via window.api.readFile().
```

This turns architectural rules into an auto-correction loop — the message tells the agent not just
*what* broke but *how* to fix it.

## Executable checks backing these constraints

List each constraint and the check that enforces it. Wire these into CI and the
`make check` / verification path.

| Constraint | Check |
|---|---|
| Renderer has no direct `fs` access | `python check_boundaries.py` (see template) |
| `<layer>` does not import `<higher layer>` | `<lint rule / grep / dependency-cruiser config>` |
| Data parsed at the boundary | `<test / lint rule>` |

> Review-feedback promotion loop: any review comment that recurs **more than twice** should be
> promoted into a new automated check here — so the harness catches it before a human does.
