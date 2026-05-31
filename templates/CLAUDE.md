# CLAUDE.md

You are working in a repository designed for long-running implementation work. Prioritize reliable
completion, continuity across sessions, and explicit verification over speed. This file is a map,
not an encyclopedia — read `docs/` on demand for detail.

## Project

- Overview: <one-paragraph purpose>
- Stack & versions: <e.g. FastAPI, PostgreSQL, Redis, SQLAlchemy 2.0>
- Detailed docs: `docs/` (read on demand)

## Operating Loop (start of every session)

1. Run `pwd`; confirm you are in the expected repository root.
2. Read `claude-progress.md` (current state, blockers, numbered Next Steps).
3. Read `decisions.md` (do not reverse past architectural choices).
4. Read `feature_list.json`; select exactly one highest-priority unfinished feature.
5. Skim `quality-document.md`; prefer fixing the lowest-graded module before building new work on it.
6. Review recent commits with `git log --oneline -5`.
7. Run `./init.sh`. If the baseline smoke / end-to-end path is already broken, fix that **first** —
   do not stack new work on a broken starting state.

Then work only on that one feature until you verify it or document why it is blocked.

## Work Rules

- One active feature at a time.
- Do not begin a second feature or do drive-by refactoring of unrelated modules while one is active.
- Do not edit feature `status` fields yourself — the verification step updates them (pass-state
  gating).
- Respect the layer boundaries in `CONSTRAINTS.md`; do not introduce cross-layer dependencies it
  forbids.
- Do not claim completion without runnable evidence.
- Do not rewrite the feature list to hide unfinished work, or remove/weaken tests to look complete.
- Use repository artifacts as the system of record.

## Verification Commands

- Tests:       `<pytest tests/ -x>`
- Type check:  `<mypy src/ --strict>`
- Lint:        `<ruff check src/>`
- Boundary:    `<python check_boundaries.py>`  (enforce `CONSTRAINTS.md`)
- Full verify: `<make check>`  (runs all of the above, including boundary checks)

## Definition of Done

A feature is done only when ALL are true: target behavior implemented; required verification
actually ran (not "code looks fine"); evidence recorded in `feature_list.json` / `claude-progress.md`;
repo remains restartable from the standard startup path.

Validation hierarchy — strict gates, do not advance on failure:

1. Unit tests pass → 2. Integration tests pass → 3. End-to-end flow passes (required for any
   cross-component change).

Completion-priority constraint: verify core functionality first. **No refactoring/optimization/style
work until it passes all three layers.**

## Repo Artifacts

- Core (read/update every session): `feature_list.json`, `claude-progress.md`, `decisions.md`,
  `init.sh`, `quality-document.md`, `clean-state-checklist.md`.
- Situational: `CONSTRAINTS.md` + `check_boundaries.py` (architecture), `sprint-contract.md` (agree
  scope before coding), `session-handoff.md` (compact handoff), `READY.md` (initialization phase),
  `evaluator-rubric.md` (an independent evaluator scores the work — not you).
- See `Template Guide.md` for how to use each.

## Session Continuity (long tasks)

Treat yourself as a shift engineer whose memory is wiped at session end. If a task will exceed ~60%
of the context window, clock out (update `claude-progress.md` + `decisions.md`, commit) and start a
fresh session from those files. On Sonnet prefer a full context reset; on Opus, compaction usually
suffices.

## Before You Stop

Run the `clean-state-checklist.md` gate — every item must pass. In short:

1. Update `claude-progress.md` and feature state.
2. Build passes; tests pass; no debug slop (`console.log`, `debugger`, `TODO`, temp logs) remains.
3. Record what is still broken or unverified.
4. Commit once the repository is safe to resume.
5. Leave a clean restart path (`./init.sh` works) for the next session.
