# Startup Readiness Checklist

Generated at the end of the **initialization phase** (a dedicated first session that does *only*
setup — no feature code). Its purpose: let a brand-new agent session read this file and immediately
know how to proceed, with **no human intervention** — satisfying the Four-Condition Rule
(can it start? can it test? can it see progress? can it pick up next steps?).

> Distinct from `clean-state-checklist.md`, which gates the *end* of every session. This file is the
> *entry* contract produced once, when the project is first scaffolded.

## 1. Start Commands

- Install dependencies: `make setup`
- Start dev server: `make dev`
- Run tests: `make test`
- Full verification: `make check`

> Prefer `make` (or another single abstraction) so the agent never has to guess between
> npm / yarn / pnpm / poetry / pipenv.

## 2. Current State

- All dependencies installed and locked
- Test framework configured (`<framework>`)
- Example test passing (1/1)  ← proves the test runner itself works
- Lint / format rules configured

## 3. Project Structure

- `src/`    — source code
- `tests/`  — test suites
- `<add the directories that matter for this project>`

---

# Initialization Acceptance Checklist

A harness gate: do **not** spawn a feature-work session until every box is checked. Completion of
initialization is measured by these conditions, not by how much code was written.

- [ ] `make setup` succeeds cleanly from a blank state
- [ ] `make test` runs and has at least one passing baseline test
- [ ] A fresh agent session can deduce "how to run" and "how to test" from repo files alone
- [ ] An ordered task breakdown exists (`feature_list.json`) with ≥3 features + acceptance criteria
- [ ] All initialization scaffolding is committed to a clean Git checkpoint
