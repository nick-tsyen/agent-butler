---
title: "Plan — Close Gaps Between Harness Guide and templates/"
date: 2026-05-31
time: "20:24"
created: 2026-05-31 20:24
status: awaiting-approval
target_dir: templates/   # top-level; references/templates/ stays pristine
source_of_truth: docs/harness-engineering-guide.md
---

# Context

We just produced `docs/harness-engineering-guide.md` — a consolidated synthesis of the 12
harness-engineering lectures, where **each `##` section ends with a "Consolidated content" drop-in
artifact** (a `CLAUDE.md`, `PROGRESS.md`, `feature_list.json`, etc.). The repo's top-level
`templates/` folder currently holds the *original course templates* (byte-identical to
`references/templates/`), which predate that synthesis and therefore **lag behind the guide**.

Goal: audit `templates/` against the guide, find what's missing, and **bring every template up to
parity with its corresponding guide "Consolidated content" block** — plus **add the template
artifacts the guide calls for that don't exist yet.** The guide's consolidated blocks are the
**target spec**; the gap is whatever a template lacks relative to its block.

Decisions confirmed with the user:
- **Scope:** update existing template files **and** add the missing ones; target = top-level
  `templates/`. Leave `references/templates/` untouched (pristine course copy). Ignore the `.zip`.
- **Naming/location:** keep template names **root-level** (e.g. `claude-progress.md`); add the
  missing decisions log as a sibling `decisions.md`. Reconcile the guide's `notes/…` example paths
  to match the root-level template names.
- **feature_list verification:** **support both** — add a machine `behavior` spec + executable
  `verification_command` for pass-state gating, while keeping the human-readable `verification`
  steps for GUI/manual flows.

> Convention note: copy-target templates (CLAUDE.md, AGENTS.md, decisions.md, READY.md,
> CONSTRAINTS.md, sprint-contract.md, clean-state-checklist.md) will **not** carry doc-style YAML
> frontmatter — the existing AGENTS.md/CLAUDE.md have none, and frontmatter would pollute a file
> copied verbatim into a user's repo. The `updated:` block inside `claude-progress.md`/`decisions.md`
> is part of the artifact's own content (the guide's required outline), not doc metadata, and stays.

---

# Gap analysis (template vs its guide "Consolidated content" block)

## A. Existing files to UPDATE

### `templates/CLAUDE.md`  — vs guide §2 (also §3, §6)
Has: Operating Loop, Rules, Required Files, one-line Completion Gate, Before You Stop.
**Gaps to close:**
- No `## Project` block (overview, stack + versions, "docs/ read on demand — map not manual").
- **No `## Verification Commands` block** (tests / type-check / lint / full-verify) — the
  highest-ROI subsystem, currently absent.
- Definition of Done is one line → expand to the **3-layer validation hierarchy** (unit →
  integration → e2e, strict gates) + **completion-priority constraint** (no refactor until core
  passes).
- Operating Loop doesn't read the decisions log → add `decisions.md`.
- Work Rules missing "no drive-by refactoring of unrelated modules" and feature-list **pass-state
  gating** ("don't edit `status` yourself").
- No brief session-continuity pointer (shift-engineer / ~60% context threshold / reset-vs-compaction).
- Keep it lean (~80 lines, map-not-manual) — target = the guide's §2 drop-in CLAUDE.md, adapted to
  root-level file names.

### `templates/AGENTS.md`  — vs guide §2
Already stronger on scope discipline (has "keep changes within selected feature scope"). **Same
gaps as CLAUDE.md:** no Verification Commands block, no 3-layer hierarchy, no completion-priority,
no `decisions.md`, no Project/stack block, no continuity pointer.

### `templates/claude-progress.md`  — vs guide §3 (⚠️ annotation 05)
Has: Current Verified State (root, startup, verification, top feature, blocker) + per-session log.
**Gaps:** Current state MUST also include **latest commit hash**, **test pass/fail counts (N/M +
failing test name)**, **lint/type-check status**; add top-level **Completed / In Progress / Known
Issues / numbered Next Steps** sections (guide's required outline); add the `updated:` timestamp
block.

### `templates/feature_list.json`  — vs guide §4 ("support both")
Has: id/priority/area/title/user_visible_behavior/status/verification(steps)/evidence/notes.
**Gaps:** add `behavior` (machine end-to-end spec) and `verification_command` (executable, for
pass-state gating) **alongside** the existing human `verification` steps; add rule
`states_changed_by_harness_only: true`; add a comment noting the VCR gate.

### `templates/clean-state-checklist.md`  — vs guide §11 (5-dimension exit)
Has: startup works, verification runs, progress recorded, feature state accurate, no half-finished,
next session continues. **Gaps:** add **Build passes** (distinct from tests) and the missing
**Artifact hygiene** dimension (no debug code / `console.log` / `debugger` / `TODO` / temp logs) —
the "stop slop / pattern-copying" item.

### `templates/quality-document.md`  — vs guide §11
Has: Product Domains + Architectural Layers tables, grading scale, change history. **Gap:** add a
**Harness Simplification** protocol section (disable one component → run benchmarks → keep/remove;
monthly cadence) — described in Template Guide but absent from the file itself.

### `templates/evaluator-rubric.md`  — vs guide §9
Already solid (6 dimensions). **Gaps:** add the **tuning note** (agents are poor self-judges; plan
3–5 tuning rounds) and **worker-checker separation** (the generator must not judge its own work);
add an **Architecture compliance** dimension to mirror §9.

### `templates/session-handoff.md`  — vs guide §11
Matches well. **Minor:** add a "Latest commit hash" line under "Verified Now" for parity with the
progress log. (Low priority.)

## B. NEW files to ADD (guide blocks with no template today)

- **`templates/decisions.md`** (§3) — decision / reason / rejected-alternatives / active-constraints
  log; paired with `claude-progress.md`.
- **`templates/READY.md`** (§5) — Startup Readiness Checklist (start commands, current state,
  structure) **plus the Initialization Acceptance Checklist** (the harness gate before feature work).
  Distinct from `clean-state-checklist.md`, which is end-of-session.
- **`templates/CONSTRAINTS.md`** (§7, +§8) — architectural invariants: layered domain rules
  (`Types → Config → Repo → Service → Runtime → UI`, forward-only imports), "enforce invariants,
  don't micromanage," and the agent-oriented **WHAT/WHY/FIX** error-message format; lists the
  executable checks that back each rule.
- **`templates/check_boundaries.py`** (§7, demonstrates §8) — sample executable boundary-check
  script that fails the build on violations and prints WHAT/WHY/FIX (adapted from the guide's
  example).
- **`templates/sprint-contract.md`** (§9) — Scope / Verification Standards / Exclusions, negotiated
  before coding.

> Not adding a separate `TASKS.md`: `feature_list.json` (with priority + `behavior` +
> `verification_command` + acceptance) already serves as the ordered task breakdown; the
> initialization-acceptance gate lives in `READY.md`. Avoids redundant scope surfaces.

## C. Documentation files to UPDATE

- **`templates/Template Guide.md`** — document each new file (How to use / What it does); refresh the
  "How to Get Started" core set; add a **"Harness Principles & Further Reading"** section that folds
  in the cross-cutting learnings that aren't copy-artifacts — §1 (five-subsystem audit &
  failure-attribution), §10 (repo = single source of truth, fresh-session test, ACID, knowledge
  hygiene), §3 continuity (60% threshold, reset vs compaction) — each with a pointer to
  `docs/harness-engineering-guide.md`.
- **`templates/index.md`** — currently a frontmatter-less duplicate of Template Guide.md; mirror the
  same updates so the two stay in sync.

## D. Reconciliation in the guide (per the naming decision)

- **`docs/harness-engineering-guide.md`** — change the §2 drop-in `CLAUDE.md` and §3 protocol/outline
  references from `notes/PROGRESS.md` / `notes/DECISIONS.md` to the root-level template names
  (`claude-progress.md`, `decisions.md`) so the guide and templates agree. Small, string-level edits.

---

# Execution order

1. Add new files (B): `decisions.md`, `READY.md`, `CONSTRAINTS.md`, `check_boundaries.py`,
   `sprint-contract.md`.
2. Update existing files (A) to parity with their guide blocks.
3. Update docs (C): `Template Guide.md` + `index.md`.
4. Reconcile guide paths (D).

All edits land in **top-level `templates/`** (and the one guide file in `docs/`). `references/` is
not touched.

# Verification

1. **JSON valid:** `python3 -c "import json; json.load(open('templates/feature_list.json'))"`.
2. **Script valid:** `python3 -m py_compile templates/check_boundaries.py`.
3. **Coverage cross-walk:** for each guide §1–§11 "Consolidated content" block, confirm a
   corresponding template file now exists/contains it (quick grep + manual tick).
4. **Map-not-manual:** `wc -l templates/CLAUDE.md templates/AGENTS.md` ≤ ~100 lines each.
5. **Hygiene dimension present:** grep `clean-state-checklist.md` for build + debug/TODO items.
6. **No leakage:** `git status` shows changes only under `templates/` and `docs/`, never
   `references/`.
7. **Drop-in cleanliness:** copy-target templates carry no doc-style YAML frontmatter; only the
   progress/decisions artifacts keep their `updated:` content block.
