# AGENTS.md

This repository is designed for long-running coding-agent work. The goal is not to maximize raw code
output — it is to leave the repo in a state where the next session can continue without guessing.
This file is a map, not an encyclopedia; read `docs/` on demand for detail.

## Project

- Overview: <one-paragraph purpose>
- Stack & versions: <e.g. FastAPI, PostgreSQL, Redis, SQLAlchemy 2.0>
- Detailed docs: `docs/` (read on demand)

## Startup Workflow

Before writing code:

1. Confirm the working directory with `pwd`.
2. Read `claude-progress.md` for the latest verified state and next step.
3. Read `decisions.md` so you do not reverse prior architectural choices.
4. Read `feature_list.json` and choose the highest-priority unfinished feature.
5. Skim `quality-document.md`; prefer fixing the lowest-graded module before building new work on it.
6. Review recent commits with `git log --oneline -5`.
7. Run `./init.sh`, then run the required smoke / end-to-end verification before starting new work.

If baseline verification is already failing, fix that first. Do not stack new feature work on top of
a broken starting state.

## Working Rules

- Work on one feature at a time.
- Do not mark a feature complete just because code was added.
- Respect the layer boundaries in `CONSTRAINTS.md`; do not introduce cross-layer dependencies it
  forbids.
- Keep changes within the selected feature scope; no drive-by refactoring of unrelated modules
  unless a blocker forces a narrow supporting fix.
- Do not edit feature `status` fields yourself — the verification step updates them (pass-state
  gating).
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts over chat summaries.

## Required Artifacts

- `feature_list.json` — source of truth for feature state
- `claude-progress.md` — session log and current verified status
- `decisions.md` — why the code is the way it is (do not reverse)
- `init.sh` — standard startup and verification path
- `quality-document.md` — module health grades; read at startup to prioritize weak modules
- `clean-state-checklist.md` — end-of-session exit gate
- `CONSTRAINTS.md` + `check_boundaries.py` — architecture boundaries and the checks that enforce them
- `sprint-contract.md` — agree scope / standards / exclusions before coding (situational)
- `session-handoff.md` — optional compact handoff for larger sessions
- `READY.md` — startup readiness, produced during the initialization phase
- `evaluator-rubric.md` — an independent evaluator scores the work (not you)

See `Template Guide.md` for how to use each.

## Verification Commands

- Tests: `<npm test / pytest>` · Type check: `<tsc --noEmit / mypy --strict>` ·
  Lint: `<eslint / ruff>` · Boundary: `<python check_boundaries.py>` (enforce `CONSTRAINTS.md`) ·
  Full verify: `<make check>`

## Definition Of Done

A feature is done only when all are true: target behavior implemented; required verification actually
ran; evidence recorded in `feature_list.json` or `claude-progress.md`; repo remains restartable from
the standard startup path.

Validation hierarchy — strict gates, do not advance on failure:

1. Unit tests pass → 2. Integration tests pass → 3. End-to-end flow passes (required for any
   cross-component change). Skipping any required level = not complete.

Completion-priority constraint: verify core functionality first. No refactoring/optimization/style
work until it passes all three layers.

## Session Continuity (long tasks)

Treat yourself as a shift engineer whose memory is wiped at session end. If a task will exceed ~60%
of the context window, clock out (update `claude-progress.md` + `decisions.md`, commit) and start
fresh from those files. On Sonnet prefer a full context reset; on Opus, compaction usually suffices.

## End Of Session

Run the `clean-state-checklist.md` gate — every item must pass. In short:

1. Update `claude-progress.md` and `feature_list.json`.
2. Build passes; tests pass; no debug slop (`console.log`, `debugger`, `TODO`, temp logs) remains.
3. Record any unresolved risk or blocker.
4. Commit with a descriptive message once the work is in a safe state.
5. Leave the repo clean enough for the next session to run `./init.sh` immediately.
