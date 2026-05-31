---
title: "Harness Engineering — Consolidated Reference Guide"
created: 2026-05-31
source: "Synthesized from references/01–12 (Learn Harness Engineering lecture series)"
description: >
  A single consolidated reference that synthesizes the 12 harness-engineering lectures,
  grouped by the repository artifact or aspect each one affects. Every section ends with a
  drop-in "Consolidated content" block you can lift straight into your repo.
tags:
  - harness-engineering
  - agents
  - claude-code
  - codex
  - reference
---

# Harness Engineering — Consolidated Reference Guide

## Central thesis

> **When a capable agent fails, it is almost never a lack of model intelligence — it is an
> infrastructure failure.** The repository *is* the specification. Anything the agent cannot see, for
> all practical purposes, does not exist. The engineer's job is **harness engineering**: designing
> the environment, expressing intent, and building feedback loops around the model — not writing
> ever-larger prompts.

A team using a fixed model (GPT-4o, ~20k LOC TS/React app) moved its success rate from **20% → near
100%** across four iterations **without changing the model** — only by adding harness components one
at a time (`AGENTS.md` → verification commands → progress files). That is the whole argument in one
data point: **what changed was the harness.**

## How to read this guide

The material is **grouped by the file or aspect it affects**, not by lecture number, so everything
about (say) `CLAUDE.md` or verification sits in one place. Every `##` section follows the same
internal contract:

- `### Problems to address` — what goes wrong without this.
- `### How to do it` — the principles and method.
- `### Actionables / implementables` — concrete steps, schemas, metrics.
- `### Consolidated content` — **the last subsection of every section**: one self-contained,
  drop-in artifact (a fenced file block, or a Markdown block to paste into `CLAUDE.md`/`docs/`) that
  merges all the instructions above it.

> [!NOTE]
> Callouts and *italicized* lines reproduced throughout are the source author's own manual
> annotations, preserved verbatim and attributed to the lecture they came from.

## Section index

1. [The Harness Mindset & Failure-Diagnosis Loop](#1-the-harness-mindset--failure-diagnosis-loop)
2. [`CLAUDE.md` / `AGENTS.md` — The Entry / Instruction File](#2-claudemd--agentsmd--the-entry--instruction-file)
3. [State Persistence — `PROGRESS.md` & `DECISIONS.md`](#3-state-persistence--progressmd--decisionsmd)
4. [Scope Control — `feature_list.json` (Feature List)](#4-scope-control--feature_listjson-feature-list)
5. [Environment & Initialization — `init.sh`, `READY.md`](#5-environment--initialization--initsh-readymd)
6. [Verification & the Definition of Done](#6-verification--the-definition-of-done)
7. [Architecture Boundaries as Executable Checks](#7-architecture-boundaries-as-executable-checks)
8. [Feedback Quality — Agent-Oriented Errors & Evidence-Backed Retries](#8-feedback-quality--agent-oriented-errors--evidence-backed-retries)
9. [Observability — Runtime & Process](#9-observability--runtime--process)
10. [Repository as Single Source of Truth & Knowledge Hygiene](#10-repository-as-single-source-of-truth--knowledge-hygiene)
11. [End-of-Session Clean Handoff & Entropy Management](#11-end-of-session-clean-handoff--entropy-management)
12. [Source coverage map](#source-coverage-map)

---

## 1. The Harness Mindset & Failure-Diagnosis Loop

*Sources: 01 (Why Capable Agents Still Fail), 02 (What a Harness Actually Is).*

A **harness** is everything in the engineering infrastructure outside the model weights. OpenAI
distills the engineer's core job into three things — **designing environments, expressing intent, and
building feedback loops**. Anthropic calls their Claude Agent SDK a "general-purpose agent harness."

### Problems to address

- Failures get blamed on the model or the prompt, so the reflex is to **swap to a more expensive
  model** — when the real bottleneck is structural.
- **"Context anxiety"**: as an agent's context window fills up, it starts rushing, skips
  verification, and picks sloppy solutions.
- Without a structured way to attribute failures, every regression is debugged from scratch.

### How to do it — the Five-Subsystem Model

A harness has five subsystems. Missing any one means an incomplete harness, and the agent will
always feel awkward to use.

| Subsystem | What it provides | Canonical artifact |
|---|---|---|
| **Instruction** | Project overview, stack + versions, first-run commands, hard constraints, doc links | `AGENTS.md` / `CLAUDE.md` |
| **Tool** | Adequate, least-privilege shell + file access (don't disable the shell "for security") | tool config |
| **Environment** | Self-describing, reproducible runtime | `pyproject.toml` / `package.json`, `.nvmrc` / `.python-version`, Docker / devcontainer |
| **State** | Progress tracking across long/multi-session tasks | `PROGRESS.md` |
| **Feedback** | Explicit verification commands (highest ROI, lowest cost) | verification block in `AGENTS.md` |

Two cross-cutting principles:

- **Give a map, not a manual.** `AGENTS.md` should be a directory page, not an encyclopedia
  (~100 lines; split into `docs/` if it overflows).
- **Constrain, don't micromanage.** Enforce executable invariants rather than enumerating
  step-by-step instructions. Anthropic found agents confidently praise their own work — so
  **separate the person who does the work from the person who checks it.**

### Actionables — the diagnostic loop & ablation test

When an agent fails or writes buggy code, **do not swap the model first.** Run a diagnostic loop and
attribute the failure to one of five structural layers:

- **Task Specification** — was the goal too vague, forcing the agent to guess?
- **Context Provision** — did it lack relevant files, or burn its window just exploring the repo?
- **Execution Environment** — did it fight broken dependencies / env setup?
- **Verification Feedback** — did it declare victory early because nothing told it the code broke?
- **State Management** — did it lose progress crossing into a new session?

Keep a simple log of these failures; fix the structural layer that caused the bottleneck.

To quantify each component's marginal value, use a **controlled-variable ablation test**: keep the
model fixed, **remove the five subsystems one at a time**, and see which removal causes the biggest
performance drop. As models get stronger, some components stop being critical — but new critical
ones always emerge.

> *Annotation (02): the ablation result "answers which component is most valuable right now — **it
> cannot, by itself, prove where the bottleneck is.** To truly locate a bottleneck, you must first
> examine failure records and attributions.** Component ablation results can only serve as supporting
> evidence.*

### Consolidated content — Harness Audit & Failure-Attribution checklist

```markdown
## Harness Audit (run when agent success rate lags)

### Five-Subsystem completeness
- [ ] Instruction: AGENTS.md / CLAUDE.md exists, ~100 lines, map not manual
- [ ] Tool: agent has least-privilege shell + file access (can run install/test/lint)
- [ ] Environment: deps locked, runtime pinned, reproducible (devcontainer/Docker)
- [ ] State: PROGRESS.md keeps long tasks from looping
- [ ] Feedback: lint / type-check / test / full-verify commands are listed and runnable

### Failure attribution (per failure, before swapping the model)
Attribute each failure to exactly one layer, then fix that layer:
1. Task Specification — goal too vague?
2. Context Provision — missing files / wasted window exploring?
3. Execution Environment — fighting broken deps/env?
4. Verification Feedback — no signal that code broke?
5. State Management — progress lost across sessions?

### Marginal-value ablation (supporting evidence only)
- Fix the model. Remove one subsystem at a time. Measure the success-rate drop.
- Biggest drop = highest current marginal value. NOTE: ablation alone does NOT
  locate the bottleneck — read failure records/attributions first.
```

---

## 2. `CLAUDE.md` / `AGENTS.md` — The Entry / Instruction File

*Sources: 01, 02, 03, 04 (Why One Giant Instruction File Fails), 06, 07, 08, 09, 12.*

This is the agent's landing page and the single most-referenced artifact across the lectures. Use
`AGENTS.md` for Codex / other agents and `CLAUDE.md` for Claude Code — same structure, different
instruction style.

### Problems to address

- **One giant file fails.** Symptoms:
  - **Low signal-to-noise ratio (SNR)** — being forced to read 50 lines of deployment notes during
    a bug fix.
  - **"Lost in the middle"** — language models statistically skip instructions buried mid-text.
  - **"Can't tell what matters"** — when every rule looks the same, the agent can't separate
    non-negotiable hard constraints from soft suggestions.
  - **Instruction debt** — rules accumulate with no owner and no expiry, like technical debt.

### How to do it

- **Map, not manual.** Keep the entry file to **50–200 lines**: high-level overview, first-run
  commands, and **≤15 non-negotiable global hard constraints**.
- **Reveal on demand.** Treat the entry file as a **router**, not an encyclopedia. Move
  domain-specific rules into topic docs (`docs/api-patterns.md`, `docs/database-rules.md`) and link
  them with a one-line description so the agent reads them only when needed.
- **Exploit "lost in the middle."** If a rule must live in the entry file, put it at the **very top
  or very bottom** — never the middle.
- **Give rules ownership and expiry.** Every rule documents its *source* (why added), *applicability*
  (when needed), and *expiry* (when it can be safely removed).
- **Constrain, don't micromanage.** Enforce invariants ("always use parameterized queries",
  "component files use PascalCase"), not implementation steps.

> [!WARNING] Annotation (04)
> **Don't duplicate type definitions, interface comments, or configuration explanations inside your
> instruction files.** Let the agent discover them naturally when it reads the source code.

### What to include — the recurring `CLAUDE.md` payload

Across the lectures, these are the blocks that repeatedly belong in the entry file:

- Project overview & purpose; tech stack **and versions**; first-run commands.
- **Verification commands** (the highest-ROI block — see §6).
- ≤15 hard constraints in explicit **MUST / MUST NOT** language.
- **Work rules**: WIP=1, no drive-by refactoring (see §4).
- **Definition of Done** + validation hierarchy (see §6).
- **Feature-list rules** (see §4).
- **Clock-in / clock-out** session routine (see §3).
- **Session-exit checklist** (see §11).

> [!NOTE] Annotation (08 / 12)
> *Artifacts must be externalized* — feature/progress state lives in machine-readable repo files, not
> in conversation text. And ⚠️ (12): **encode the session-exit checklist directly into `CLAUDE.md`**,
> not into a human's memory.

### Consolidated content — drop-in `CLAUDE.md`

```markdown
# CLAUDE.md

You are working in a repository designed for long-running implementation work. Prioritize reliable
completion, continuity across sessions, and explicit verification over speed.

## Project
- Overview: <one-paragraph purpose>
- Stack & versions: <e.g. FastAPI, PostgreSQL, Redis, SQLAlchemy 2.0>
- Detailed docs: see docs/ (read on demand — this file is a map, not an encyclopedia)

## Operating Loop (Clock-In)
At the start of EVERY session, before writing any code:
1. Run `pwd`; confirm you are in the repo root.
2. Read `claude-progress.md` (current state, blockers, numbered Next Steps).
3. Read `decisions.md` (do not reverse past architectural choices).
4. Read `feature_list.json`; pick the single highest-priority unfinished feature.
5. Review recent commits: `git log --oneline -5`.
6. Run `./init.sh`; if baseline verification fails, fix that FIRST.

## Work Rules
- Work on exactly ONE feature/task at a time (WIP=1).
- Do NOT start feature B or do drive-by refactoring of unrelated modules while on feature A.
- Do NOT modify feature-list `state` fields yourself — the verification step updates them.
- Do NOT remove/weaken tests or rewrite the feature list to hide unfinished work.
- Constrain to invariants; let source code carry type/config detail.

## Verification Commands
- Tests:       pytest tests/ -x
- Type check:  mypy src/ --strict
- Lint:        ruff check src/
- Full verify: make check   # runs all of the above

## Definition of Done
A feature is done ONLY when ALL are true:
- target behavior implemented;
- required verification ACTUALLY ran (not "code looks fine");
- evidence recorded in feature_list.json / claude-progress.md;
- repo remains restartable from the standard startup path.
Verification hierarchy (strict gates — do not advance on failure):
1. Unit tests pass  →  2. Integration tests pass  →  3. End-to-end flow passes
No refactoring/optimization until core functionality passes all three layers.

## Feature List Rules
- Source of truth: feature_list.json
- Only ONE feature may be `in_progress` at a time.
- A feature moves to `passing` only after its verification command succeeds (pass-state gating).

## Before You Stop (Clock-Out / Session Exit)
1. Update claude-progress.md (state, test counts, next steps).
2. Update feature_list.json state.
3. Record anything still broken or unverified.
4. Build passes; tests pass; no debug/TODO slop; standard startup path works.
5. Commit completed work with a descriptive message; leave a clean restart path.
```

---

## 3. State Persistence — `PROGRESS.md` & `DECISIONS.md`

*Sources: 02, 05 (Keeping Context Alive Across Sessions).*

> **Treat the agent like a shift engineer whose short-term memory is wiped at the end of every
> session.** Before it "clocks out," it must write down critical information so the next "shift" can
> pick up quickly.

### Problems to address — what happens when continuity breaks

- **Re-deciding**: a prior session analyzed three options and chose B; the new session, lacking that
  context, may re-decide and pick A. Same information, different conclusion.
- **Duplicate work / rework**: the agent redoes finished work, or does half, hits a conflict, and
  reworks.
- **Silent drift**: each session's understanding of the goal shifts slightly; deviations compound.
- **Verification gap**: prior pass/fail results weren't recorded, so every session re-diagnoses from
  scratch.

### How to do it

- **Clock-in / clock-out protocol** (see consolidated block).
- **60% context threshold**: short tasks (<30 min / <60% window) finish in-session; long tasks
  (>60%) clock out and start fresh from persistence files.
- **Reset vs compaction by model**: on **Sonnet** (severe context anxiety) prefer a **Context
  Reset** (clear and rebuild from files); on **Opus** (diminished anxiety) **compaction**
  (summarizing the early session) is usually enough.

> [!HINT] Annotation (05)
> The 60% handoff exists to prevent **"context anxiety"** — a documented phenomenon where agents
> nearing their token limits start rushing, skipping verification, and picking suboptimal solutions.

> *Annotation (05): **Your primary metric for harness efficiency is Rebuild Cost** — the time a fresh
> session needs to reach an executable state. A good harness compresses this from ~15 minutes of
> aimless exploration to **under 3 minutes** of targeted reading and validation.*

### Actionables / implementables

- **`PROGRESS.md`** — the handoff log. ⚠️ (05) **must include**: latest commit hash, current test
  pass/fail status, explicit Completed vs In-Progress lists, known blockers, and a **numbered Next
  Steps** list (specific enough that a fresh session can act immediately).
- **`DECISIONS.md`** — a lightweight log of *what was decided, why, which alternatives were rejected,
  and any active constraints*. Prevents a new session from "optimizing away" deliberate design.
- **Git commits as checkpoints** — commit after every atomic unit of work; messages explain *what*
  and *why*. Free, automatically versioned state snapshots. Never batch unrelated changes.

### Consolidated content — `PROGRESS.md` + `DECISIONS.md` + continuity protocol

````markdown
## Session Continuity (Long-Running Tasks)
Treat yourself as a shift engineer whose memory is wiped at session end. Use this protocol for any
task spanning multiple sessions or estimated to consume >60% of the context window.

### Clock-In (Session Start)
1. Read claude-progress.md — exact status, blockers, numbered Next Steps.
2. Read decisions.md — do not reverse prior architectural decisions.
3. Run the validation command (make check / pytest / npm test) — confirm a consistent repo.
4. Resume from claude-progress.md "Next Steps".

### Clock-Out (Before Session End or ~60% context)
1. Update claude-progress.md (schema below).
2. Run validation; record pass/fail counts in the file.
3. Commit completed units of work with atomic, descriptive messages.

### Context Reset Strategy
- Short tasks (<30 min / <60% window): complete in-session.
- Long tasks (>60% window): clock out, start fresh, clock in from files.
- Sonnet: prefer Context Reset. Opus: Compaction usually sufficient.
````

```markdown
---
updated: YYYY-MM-DD HH:MM
---
# Project Progress

## Current State
- Latest commit: <hash> (<short description>)
- Test status: <N>/<M> passing (<name of any failing test>)
- Lint / type-check: passing | failing

## Completed
- [x] <item>

## In Progress
- [ ] <item> (<% done> — <one-line blocker if any>)

## Known Issues
- <issue and context>

## Next Steps
1. <first action — specific enough that a fresh session can act on it immediately>
2. ...
```

```markdown
---
updated: YYYY-MM-DD HH:MM
---
# Design Decisions

## YYYY-MM-DD: <Decision title>
- **Decision:** <what was chosen>
- **Reason:** <why>
- **Rejected alternatives:** <option> — <why rejected>
- **Active constraints:** <any constraints that must remain>
```

---

## 4. Scope Control — `feature_list.json` (Feature List)

*Sources: 07 (Draw Clear Task Boundaries), 08 (Feature Lists as Harness Primitives).*

> Annotation (08): *Feature lists, in many people's eyes, are just a memo. But in the harness world,
> a feature list isn't a memo for humans — **it's the foundational structure the entire harness is
> built on.** The scheduler picks tasks from it, the verifier judges completion against it, the
> handoff reporter generates summaries from it. Without it, these components have no shared consensus
> to depend on.* And: ***artifacts must be externalized*** — feature state lives in a machine-readable
> repo file, not in conversation text.

### Problems to address

- **Overreach**: the agent activates more tasks than optimal — "doing 5 features with 0 passing
  end-to-end." Born from an impulse to "do a little extra."
- **Under-finish**: code written but tests not passing; the ratio of end-to-end-passing tasks falls
  below threshold.

> *Annotation (07): Anthropic — "when prompts are too broad, agents tend to start multiple things at
> once rather than finish one first." OpenAI — **tasks without explicit scope controls see
> completion rates plummet.** This is not a model problem — it's a harness problem. You didn't draw
> the boundary.*

### How to do it

- **WIP=1**: the harness enforces a single-task loop. The agent may not open a new context or pull a
  second task until the active one verifiably passes.
- **Triple structure** — every item carries `(behavior description, verification command, state)`.
  Missing any element makes the item incomplete.
- **4-state machine** — `not_started`, `in_progress`/`active` (only one at a time), `blocked`,
  `passing`.
- **Pass-state gating** — *state transitions are controlled by the harness, not freely changed by
  the agent.* The only way `active → passing` is the verification command succeeding; once
  `passing`, it can't go back.
- **Granularity = one session** — "User can add items to cart" (good). "Implement the shopping
  cart" (too broad). "Create the name field on the Cart model" (too narrow).

> [!TIP] Annotation (07) 💡 **Scope Surface**
> A DAG where each node is a work unit and edges are dependencies; node states limited to four:
> `not_started`, `active`, `blocked`, `passing`. And: *every task item must map to an explicit,
> executable command that evaluates the actual runtime behavior of the system.*

### Actionables / implementables

- A single machine-readable file (`feature_list.json` or `/docs/features.md`) as the absolute source
  of truth for scope.
- **Verified Completion Rate (VCR)** = Verified Tasks / Activated Tasks. If VCR < 1.0 (an active task
  opened but not passing), the harness **blocks activation of any new node**, forcing focus back onto
  finishing.
- Feature-list rules pinned in `CLAUDE.md` (see §2).

### Consolidated content — `feature_list.json` + rules block

```json
{
  "project": "replace-with-project-name",
  "last_updated": "YYYY-MM-DD",
  "rules": {
    "single_active_feature": true,
    "passing_requires_evidence": true,
    "do_not_skip_verification": true
  },
  "status_legend": {
    "not_started": "Work has not begun.",
    "in_progress": "The single current active task.",
    "blocked": "Cannot continue until a documented blocker is resolved.",
    "passing": "Verification passed and evidence is recorded."
  },
  "features": [
    {
      "id": "F03",
      "priority": 1,
      "area": "cart",
      "title": "Add item to cart",
      "user_visible_behavior": "A user can add an item and see it in the cart.",
      "behavior": "POST /cart/items with {product_id, quantity} returns 201",
      "status": "not_started",
      "verification": "curl -X POST http://localhost:3000/api/cart/items -H 'Content-Type: application/json' -d '{\"product_id\":1,\"quantity\":2}' | jq '.status == 201'",
      "evidence": [],
      "notes": ""
    }
  ]
}
```

```markdown
## Feature List Rules
- Feature list file: feature_list.json (or /docs/features.md)
- Only ONE feature may be `in_progress`/`active` at a time.
- Each item MUST carry the triple: behavior + verification command + state.
- Do NOT modify feature states yourself — the verification step updates them (pass-state gating).
- A feature is complete only when its specific verification command passes flawlessly.
- Calibrate granularity to "completable in one session."
- Harness gate: if Verified Completion Rate (verified/activated) < 1.0, block activating new nodes.
```

---

## 5. Environment & Initialization — `init.sh`, `READY.md`

*Sources: 02, 06 (Make the Agent Initialize Before Every Work Session).*

### Problems to address — what happens when init and feature work are mixed

- **Fragile infrastructure**: *the agent prioritizes feature code (80% effort) over infrastructure
  (20%)*, leaving test frameworks unverified and no progress files.
- **Downstream context loss**: the second session inherits a broken loop — it can't run the project,
  tests, or determine state.
- **Unverified accumulation**: features written before the test framework is configured get torn
  down and refactored later.
- **Wasted context budget**: early config eats the window; session 1 finishes partial features and
  session 2 re-learns the structure.
- **Implicit-assumption landmines**: *crucial setup choices go unrecorded*, so a later session
  introduces Jest into a Vitest project — doubling maintenance.

> *Annotation (06): **Implementation and initialization have conflicting optimization targets.** Left
> to its own devices, an agent prioritizes visible feature output over robust, reusable
> infrastructure.*

### How to do it

- **Dedicated initialization phase** — the first session does **only** initialization; **no business
  feature code at all.**
- **Start from a template** (create-react-app, fastapi-template, …) to preset structure, deps, and
  test framework; bake common steps in so only project-specific init remains.
- **`make` abstraction** — uniform entry points (`make setup`, `make test`) so the agent never has to
  guess between npm/yarn/pnpm/poetry/pipenv.
- **The Four-Condition Rule** — initialization is complete (regardless of LOC) when the repo alone
  answers: **Can it start? Can it test? Can it see progress? Can it pick up next steps?**

### Actionables / implementables

Initialization must produce five artifacts: a runnable environment (deps installed & locked); a
verifiable test framework (≥1 example test passes); a startup-readiness checklist; an ordered task
breakdown with acceptance criteria; and a clean git checkpoint. Lock the environment to be
self-describing (`pyproject.toml`/`package.json`, `.nvmrc`/`.python-version`, devcontainer).

### Consolidated content — `init.sh` + `READY.md` + acceptance checklist

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Replace with your repository's real commands.
INSTALL_CMD=(npm install)
VERIFY_CMD=(npm test)
START_CMD=(npm run dev)

echo "==> Working directory: $PWD"
echo "==> Syncing dependencies";    "${INSTALL_CMD[@]}"
echo "==> Baseline verification";   "${VERIFY_CMD[@]}"
echo "==> Startup command:";        printf '    %q' "${START_CMD[@]}"; printf '\n'

if [ "${RUN_START_COMMAND:-0}" = "1" ]; then
  echo "==> Starting the app"; exec "${START_CMD[@]}"
fi
echo "Set RUN_START_COMMAND=1 to launch the app directly."
# If verification fails, STOP and fix the baseline before any feature work.
```

```markdown
# READY.md — Startup Readiness Checklist (generated at end of init phase)

## 1. Start Commands
- Install: `make setup`   - Dev server: `make dev`
- Tests:   `make test`    - Full verify: `make check`

## 2. Current State
- All dependencies installed and locked
- Test framework configured (<framework>)
- Example test passing (1/1)
- Lint/format rules configured

## 3. Project Structure
- src/    — source code
- tests/  — test suites

# Initialization Acceptance Checklist (harness gate before feature work)
- [ ] `make setup` succeeds cleanly from a blank state
- [ ] `make test` runs with ≥1 passing baseline test
- [ ] A fresh agent session can deduce "how to run / test" from repo files alone
- [ ] Task breakdown file exists with ≥3 tasks + acceptance criteria
- [ ] All init scaffolding committed to a clean git checkpoint
```

---

## 6. Verification & the Definition of Done

*Sources: 01, 09 (Preventing Agents from Declaring Victory Too Early), 10 (Only a Full Pipeline Run
Counts).*

> [!NOTE] Annotation (09) — Modern neural networks are systematically overconfident
> Guo et al. (2017, ICML) proved that modern neural networks report confidence significantly higher
> than their actual accuracy. AI coding agents are no different — they "feel" done while far from it.
> **Your harness must replace the agent's "feelings" with externalized, execution-based
> verification.**

### Problems to address

- **Premature completion**: the agent judges completion on local, code-level confidence; system-level
  correctness requires global verification.
- **Confidence calibration bias**: for complex multi-file tasks, the agent is consistently more
  confident than its performance warrants.
- **Passing unit tests ≠ task complete** (the most dangerous trap). Unit-test isolation/mocking is
  precisely what hides cross-component bugs:
  - **Interface mismatch** (relative vs absolute path between renderer and preload),
  - **State propagation** (ORM cache holds the old schema after a migration),
  - **Environment dependency** (mocked tests pass; real config/network/service fails).

> [!WARNING] Annotation (09)
> **Never allow the agent to judge its own completion status based on code appearance or local
> confidence.** Hardcode an objective, executable set of exit conditions in `CLAUDE.md`. And:
> ***do not let the generating agent check its own work*** — use an independent, highly critical
> evaluator or a hardcoded test suite as gatekeeper.

### How to do it

- **Externalize the Definition of Done** as an executable verification hierarchy.
- **Three-layer termination validation** with strict gates (do not advance on failure):
  1. **Syntax & static analysis** (cheap linters/type-checkers first),
  2. **Runtime behavior** (start the app, run unit tests, check startup health),
  3. **System-level confirmation** (full E2E user-scenario simulation, e.g. Playwright).
- **Completion-Priority Constraint**: first correctness, then performance, then style. **No
  refactoring or optimization until core functionality passes all three layers.**
- **Worker-Checker separation**: a **Planner → Generator → Evaluator** split delivers fully
  functional, end-to-end-validated features where a single bare agent fails via premature hand-off.

### Actionables / implementables

- Make E2E **non-negotiable** for any change touching more than one isolated component — "only a full
  pipeline run counts as real verification." (Real case: 5 defects — interface mismatch, state
  propagation, resource leak, permission, error propagation — all caught by E2E, none by unit tests;
  test time rose 2s → 15s, perfectly acceptable in an agent workflow.)

### Consolidated content — Definition of Done + validation hierarchy

```markdown
## Definition of Done
- Feature complete = end-to-end verification passed, NOT "code is written".
- The agent never marks its own work done by inspection; an independent checker / test suite gates it.

## Validation Hierarchy (strict gates — skipping any required level = NOT complete)
- Level 1: Syntax & static analysis (lint, type-check)        — must pass
- Level 2: Runtime behavior (app starts, unit + integration)  — must pass
- Level 3: End-to-end flow (full user scenario, e.g. Playwright)
           — MUST pass whenever cross-component changes are involved
- Do not proceed to Level N+1 while Level N fails.

## Completion-Priority Constraint
- Verify functional correctness FIRST. No refactoring/optimization/style work
  until core functionality passes all three layers.

## Worker–Checker Separation
- Prefer Planner → Generator → Evaluator. The generator must not be its own judge.
```

---

## 7. Architecture Boundaries as Executable Checks

*Source: 10 (Only a Full Pipeline Run Counts as Real Verification).*

> [!NOTE] Annotation (10) — OpenAI's experience
> For agent-generated codebases, **architectural constraints must be established as early
> prerequisites on day one** — not once the team has grown. The reason: **agents copy existing
> patterns in the repository, even when those patterns are inconsistent or suboptimal.** Without
> constraints, agents introduce more drift with every session.

### Problems to address

- **Doc-only rules are invisible** to both agents and busy engineers: *"if a rule cannot be
  mechanically broken in a build pipeline, it does not exist."*
- **Pattern-copying drift** compounds every session.
- A tangled architecture makes E2E meaningless — it only proves "the whole mess runs."

### How to do it

- **Define boundaries before writing E2E tests.**
- **Layered Domain Architecture** — fixed forward-flowing layers:
  `Types → Config → Repository → Service → Runtime → UI`. **A layer may only import from layers below
  it.** Cross-domain concerns enter through explicit Providers interfaces; anything else is forbidden
  and mechanically enforced via custom linting.
  - **Types/Models**: pure declarations; zero dependencies.
  - **Config**: static env/flags/constants; imports Types only; no execution logic.
  - **Repository**: talks to DB/APIs/filesystem; imports Config + Types; no business rules.
  - **Service**: the brain — coordinates repos, applies validation; agnostic of how it's invoked.
  - **UI**: renders state, captures intent; only calls Service.
- **Enforce invariants; don't micromanage** (e.g. "data is parsed at the boundary," not "use library
  X").
- **Review-feedback promotion loop**: a review comment seen **more than twice** becomes an automated
  lint/regex/integration check shipped into CI — so the system catches it before a human does.

### Actionables / implementables

- Turn every architectural constraint into a test or lint rule (Dependency Cruiser, custom AST, or a
  simple grep that fails the build):
  ```bash
  grep -r "require('fs')" src/renderer/ && exit 1 || echo "OK: no direct fs access in renderer"
  ```

### Consolidated content — `CONSTRAINTS.md` + boundary-check script

```markdown
# CONSTRAINTS.md — Architectural Invariants (mechanically enforced)
Layering (import only from layers BELOW you):
  Types → Config → Repository → Service → Runtime → UI
- UI imports Service only; never Repository/Config/fs directly.
- Repository imports Config + Types; contains zero business validation.
- Cross-domain access goes through explicit Providers interfaces — nothing else.
Invariant style: enforce outcomes ("parse data at the boundary"), not implementations.
Every rule here has a corresponding executable check in CI (below).
```

```python
import os, sys

def check_architectural_boundary(directory="src/renderer"):
    violations, forbidden = [], "import fs from"
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(('.ts', '.tsx', '.js', '.jsx')):
                path = os.path.join(root, f)
                with open(path, encoding='utf-8') as fh:
                    for n, line in enumerate(fh, 1):
                        if forbidden in line:
                            violations.append((path, n))
    if violations:
        for path, n in violations:
            print(f"ERROR: Direct filesystem access in {path}:{n}")
            print("WHY: The renderer layer must stay decoupled from OS operations.")
            print("FIX: Move file logic to src/preload/file-ops.ts; call via window.api.")
        sys.exit(1)
    print("Architecture check passed: no direct 'fs' imports in renderer.")

if __name__ == "__main__":
    check_architectural_boundary()
```

---

## 8. Feedback Quality — Agent-Oriented Errors & Evidence-Backed Retries

*Sources: 09, 10, 11 (Making the Agent's Runtime Observable).*

### Problems to address

- Generic failures (`Test failed: expected 200, got 500`) make agents loop blindly or give up.
- Vague evaluator feedback ("it doesn't feel right", "the build failed") turns retries into random
  guesses that alter working code and burn tokens.
- The **session-handoff information cliff**: when work fails and is handed off, missing context means
  the next session re-diagnoses from scratch — **30–50% of session time wasted**.

### How to do it

- Every error message contains three elements: **what went wrong / why it matters / how to fix it.**

> [!TIP] Annotation (10) — error messages written for agents must include fix instructions
> Instead of `"Direct filesystem access in renderer"`, write: *"Direct filesystem access in renderer.
> All file operations must go through the preload bridge. Move this call to `preload/file-ops.ts` and
> invoke via `window.api`."* This turns architectural rules into an **auto-correction loop**.

- Transform raw failures into **structured, quantifiable evidence packets** before passing them back
  to the generator, then **lock scope** on retry ("modify only the relevant code; do not alter
  unrelated working functions").

> [!TIP] Annotation (11) 💡
> *If an evaluation fails, the harness must inject exact, evidence-backed metrics back to the
> generator to guide the retry precisely.*

### Actionables / implementables — vague vs evidence-backed

| Dimension | Anti-pattern (avoid) | Engineering pattern (inject) |
|---|---|---|
| Visual / UI | "The layout looks broken on mobile." | `{"element":"button#submit","property":"contrast-ratio","expected":">= 4.5:1","actual":"2.1:1","viewport":"375x812"}` |
| Performance | "The page loads too slowly." | `{"metric":"TTFB","threshold_ms":200,"measured_ms":650,"bottleneck_trace_id":"span_99a8b"}` |
| Testing | "Some unit tests failed in auth." | `{"test_file":"auth_test.py","line":42,"assertion":"assert user.is_authenticated","stdout":"ValueError: Missing JWT secret"}` |

### Consolidated content — error format + evidence-packet schema

```markdown
## Agent-Oriented Error Format (every failure message must contain)
WHAT: <what went wrong, with file:line>
WHY:  <why it matters / which invariant it violates>
FIX:  <concrete corrective step the agent can execute>

Example:
ERROR: Found direct import of 'fs' in src/renderer/App.tsx:12
WHY:   Renderer process has no Node.js API access (security/portability).
FIX:   Move file ops to src/preload/file-ops.ts and call via window.api.readFile().
```

```json
// Evidence packet injected back to the generator on failure (then lock scope)
{
  "dimension": "UI/UX Compliance",
  "target": "WCAG AA contrast >= 4.5:1",
  "measured": "2.1:1",
  "evidence_clip": "<exact DOM snippet / log / stack trace>",
  "instruction": "Modify ONLY code resolving this metric. Do not touch unrelated working functions."
}
```

---

## 9. Observability — Runtime & Process

*Source: 11 (Making the Agent's Runtime Observable).*

> Annotation (11): **Without observability, agents make decisions under uncertainty, evaluations
> become subjective judgments, and retries become blind wandering.** Both OpenAI and Anthropic frame
> reliability as an evidence problem.

### Problems to address

- Can't distinguish **"correct" from "looks correct"** — code review shows what was *written*;
  runtime tracing shows what actually *ran*.
- **Evaluation becomes mysticism** — without rubrics, the same output gets wildly different
  assessments; quality becomes non-reproducible.
- **Retries become blind guesses**; every blind retry burns tokens and time.
- **Session-handoff information cliff** (30–50% of session time on redundant diagnosis).

### How to do it — double-layered observability

| Layer | Answers | Core artifacts |
|---|---|---|
| **Runtime observability** | *What* did the system actually do? | logs, traces, process events, health checks |
| **Process observability** | *Why* should this change be accepted? | sprint contracts, upfront plans, scoring rubrics, acceptance criteria |

> [!WARNING] Annotation (11)
> **Do not rely on the agent to print its own logs or manage its own tracking.** Agents have blind
> spots and inconsistent log formats. The harness must automatically capture: application-lifecycle
> states, feature-path execution (entry/checkpoint/exit), data flow, resource utilization, and full
> error context — not just surface strings.

- **Sprint contract**: before any code, the generator and evaluator negotiate Scope / Verification
  Standards / Exclusions.
- **Evaluator rubric**: replace "it feels right" with dimension-based grading (A–D) and rigid
  thresholds; failing any one dimension triggers failure.
- **OpenTelemetry mapping**: **Trace = a harness session**, **Span = a task**, **Sub-span = each
  verification / test / compile step** — so telemetry integrates with Jaeger/Zipkin.

### Consolidated content — sprint contract + evaluator rubric + tracing map

```markdown
# Sprint Contract: <feature>
## Scope
- <components/files to modify>
## Verification Standards
- <e.g. visual regression passes; main-flow E2E passes; no FOUC>
## Exclusions
- <what NOT to handle — e.g. print styles, third-party component theming>

# Evaluator Rubric (fail if ANY dimension is below threshold)
| Dimension              | A                 | B               | C            | D          |
|------------------------|-------------------|-----------------|--------------|------------|
| Code correctness       | All tests pass    | Main flow passes| Partial pass | Build fails|
| Architecture compliance| Fully compliant   | Minor deviation | Obvious dev. | Violations |
| Test coverage          | Main + edge cases | Main flow only  | Skeleton only| No tests   |

# OpenTelemetry mapping
- Trace    = one complete harness session
- Span     = one task / feature block
- Sub-span = one verification / test run / compile step
```

---

## 10. Repository as Single Source of Truth & Knowledge Hygiene

*Sources: 02, 03 (Making the Repo the Single Source of Truth), 04.*

> [!NOTE] Annotation (03)
> **If it isn't in the repository, it does not exist to the agent.** Stop pinning critical rules in
> Slack or burying specs in Confluence.

### Problems to address

- **Knowledge-visibility gap**: the share of project knowledge *not* in the repo. The bigger the gap,
  the higher the failure rate. (Real case: architecture decisions scattered across Confluence/Slack/
  engineers' heads → 70% of tasks needed human intervention, nearly all from violating implicit
  constraints "everyone knows but nobody wrote down.")
- **Discovery cost**: *the more hidden the information, the higher the cost to find it, and the less
  budget remains for the actual task.*
- **Knowledge decay**: *documentation drifting out of sync with code is the biggest enemy — worse
  than no documentation is documentation that's out of date.*

### How to do it

- **Repo = system of record.** The repo has the final say; nowhere else counts.
- **Knowledge lives next to code.** *Put a short doc in each module directory explaining its
  responsibilities, interfaces, and special constraints* — the directory is a natural index, so
  reaching the code reaches the constraints (no searching, low discovery cost).
- **Fresh-session test**: open a blank session with only the repo and ask five questions — *What is
  this system? How is it organized? How do I run it? How do I verify it? Where are we now?* Blank
  answers = blank spots in the map; fix them.
- **Minimal but complete**: *if removing a rule doesn't affect the agent's decision quality, that
  rule shouldn't exist* — but every fresh-session question must have an answer.
- **Update with code**: bind doc updates to code changes (same commit); CI/pre-commit reminder when
  module code changes.
- **ACID discipline for agent state**:
  - **Atomicity** — one logical operation = one commit; fail midway → `git stash`/reset. No "half
    done."
  - **Consistency** — verify after each operation; *inconsistent intermediate states should not be
    committed.*
  - **Isolation** — concurrent agents use separate branches/progress files; *concurrent writes to the
    same file are a common source of trouble.*
  - **Durability** — *critical project knowledge lives in git-tracked files;* what's in your head
    doesn't count.

### Consolidated content — repo layout + fresh-session test + ACID rules

```text
project/
├── AGENTS.md / CLAUDE.md   # entry: overview, run commands, hard constraints (map, not manual)
├── src/
│   ├── api/ARCHITECTURE.md  # API-layer architecture decisions (next to the code)
│   └── db/CONSTRAINTS.md    # DB hard constraints in MUST/MUST NOT language
├── claude-progress.md       # done / in-progress / blocked / next steps
├── decisions.md             # decision / reason / rejected alternatives / constraints
├── feature_list.json        # scope source of truth
└── Makefile / init.sh       # standardized: setup, test, lint, check
```

```markdown
## Fresh-Session Test (the map must answer all five from repo contents alone)
1. What is this system?      → AGENTS.md / README
2. How is it organized?      → ARCHITECTURE.md / module docs
3. How do I run it?          → Makefile / init.sh / package scripts
4. How do I verify it?       → test, lint, check commands
5. Where are we now?         → PROGRESS.md / feature_list.json / git history

## ACID rules for agent state
- Atomicity:   one logical op = one commit; roll back on mid-way failure.
- Consistency: verify after each op; never commit inconsistent intermediate states.
- Isolation:   concurrent agents → separate branches/progress files (avoid same-file writes).
- Durability:  knowledge that must survive sessions is written to git-tracked files.

## Knowledge hygiene
- Update docs in the SAME commit as the code; add a CI/pre-commit doc-drift reminder.
- Minimal but complete: drop any rule that doesn't change a decision; answer every fresh-session Q.
```

---

## 11. End-of-Session Clean Handoff & Entropy Management

*Sources: 05, 12 (Leave a Clean Handoff at the End of Every Session).*

> Annotation (12): Technical debt and repository entropy grow exponentially unless strictly managed
> at the end of *every* session. ⚠️ During five months of Codex experiments OpenAI observed that
> **agents copy patterns already present in the repository, even when those patterns are inconsistent
> or suboptimal** — the coffee-cup effect: one mess invites the next.

### Problems to address

- **Entropy / AI slop** accumulates; manual Friday cleanups (OpenAI initially spent 20% of every
  Friday) don't scale.
- A session that "compiles" or has one working feature is **not** done if it leaves the repo
  unbuildable, untracked, or full of debug slop for the next session.

### How to do it

- **5-dimension session-exit checklist** (gate completion on all five):

  | Dimension | Action | Goal |
  |---|---|---|
  | Build status | run build | next session doesn't inherit an unbuildable repo |
  | Test suite | run full tests | no regressions introduced |
  | Progress tracking | update feature list / next steps | cut next-session diagnostic time 60–80% |
  | Artifact hygiene | delete temp logs, debug stmts, TODO markers | stop slop / pattern-copying |
  | Startup path | verify standard init works | immediate continuity, no manual fixes |

- **Dual-mode cleanup**: **immediate** (end of every session — like reference-counting GC: clean your
  own side effects) + **periodic** (weekly — like tracing GC: full scan, structural divergence, flaky
  tests, refactor PRs).
- **Idempotent cleanup scripts** — safe to run repeatedly (`rm -f`, `git checkout -- .env.local`,
  re-verify).
- **Live `QUALITY.md`** — an active, machine-readable doc grading each module/domain/layer (A–D) on
  verification, agent legibility, test stability, boundary compliance. New sessions read it first and
  **fix the lowest-scoring module before building on compromised code.**
- **Continuous harness simplification** — every component encodes an assumption about what the model
  *can't* do; as models improve, assumptions go stale. Monthly: disable one component, run benchmarks;
  if metrics hold, delete it. (Anthropic removed sprint-splitting when Opus 4.6 could decompose work
  itself — the builder then ran 2+ hours without drifting. But the **evaluator still earned its keep**
  near the model's capability boundary, catching stubs/missing functionality.)
- **High-throughput merge philosophy** — when agent output far exceeds human review (e.g. 3.5+ PRs/
  day), minimize blocking gates: short-lived PRs, resolve flakiness on re-run. Criterion: **average
  cost of fixing a bug vs average cost of waiting for human review** — when the former is lower, merge
  fast. (Caveat: irresponsible in a low-throughput environment.)

> A deeper principle (12): *as models improve, the interesting combinations in a harness don't shrink
> — they shift.* Problems get absorbed by model capability; new capability boundaries open new design
> space. The engineer's job is to keep finding the next valuable combination.

### Consolidated content — exit checklist + cleanup script + `QUALITY.md` + handoff note

```markdown
## Session Exit Checklist (session complete = task verified AND all five pass)
- [ ] Build passes (e.g. npm run build)
- [ ] All tests pass (e.g. npm test)
- [ ] Feature list / PROGRESS.md updated
- [ ] No debug slop remaining (console.log, debugger, TODO, temp logs)
- [ ] Standard startup path works (e.g. npm run dev / ./init.sh)
```

```bash
# Idempotent cleanup (safe to re-run on failure/retry)
rm -f /tmp/debug-*.log          # -f: no error if missing
git checkout -- .env.local      # restore to known baseline
npm run test                    # verify cleanup didn't break anything
```

```markdown
# QUALITY.md (grade A–D; new sessions fix the lowest-scoring module first)
| Domain / Layer | Grade | Verification | Agent Legibility | Test Stability | Key Gaps | Updated |
|----------------|-------|--------------|------------------|----------------|----------|---------|
| User Auth      | A     | Yes          | Yes              | Stable         | —        | <date>  |
| Payment        | C     | Partial      | Hard (3 files)   | 2 flaky tests  | callbacks untested | <date> |

# Session Handoff note (optional; valuable for long/multi-area sessions)
## Verified Now: <working + what verification ran>
## Changed This Session: <code + harness changes>
## Broken/Unverified: <defects, risky paths>
## Next Best Step: <highest-priority feature, what counts as passing, what NOT to touch>
## Commands: <startup / verification / focused debug>

# Harness Simplification (monthly)
- Disable one component → run benchmark suite → if grades hold, delete it; else restore/lighten.
```

---

## Source coverage map

Every lecture maps to at least one section; cross-cutting lectures appear in several.

| Lecture | Title | Primary section(s) |
|---|---|---|
| 01 | Why Capable Agents Still Fail | §1, §2, §6 |
| 02 | What a Harness Actually Is | §1, §2, §3, §5, §10 |
| 03 | Making the Repo the Single Source of Truth | §10, §2 |
| 04 | Why One Giant Instruction File Fails | §2, §10 |
| 05 | Keeping Context Alive Across Sessions | §3, §11 |
| 06 | Make the Agent Initialize Before Every Work Session | §5 |
| 07 | Draw Clear Task Boundaries for Agents | §4 |
| 08 | Use Feature Lists to Constrain What the Agent Does | §4, §2 |
| 09 | Preventing Agents from Declaring Victory Too Early | §6, §8 |
| 10 | Only a Full Pipeline Run Counts as Real Verification | §7, §6, §8 |
| 11 | Making the Agent's Runtime Observable | §9, §8 |
| 12 | Leave a Clean Handoff at the End of Every Session | §11, §2 |

> The `references/templates/` artifacts (`AGENTS.md`, `CLAUDE.md`, `init.sh`, `claude-progress.md`,
> `feature_list.json`, `session-handoff.md`, `clean-state-checklist.md`, `evaluator-rubric.md`,
> `quality-document.md`) are the realized, ready-to-copy versions of the consolidated blocks above.
