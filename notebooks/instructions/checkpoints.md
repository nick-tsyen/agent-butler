## Session Continuity

---

### Clock-In (Session Start)

Before touching any code, always:

1. Read `notes/PROGRESS.md` — understand exact status, known blockers, and the numbered Next Steps list.
2. Read `notes/DECISIONS.md` — do not reverse or "optimize away" prior architectural decisions.
3. Run the project's validation command (e.g., `make check`, `pytest`, `npm test`) to confirm the
   repo is in a consistent state.
4. Resume from the "Next Steps" section in `PROGRESS.md`.

---

### Clock-Out (Before Session End or Context Reset)

Before ending a session or when context reaches ~60%, always:

1. Update `notes/PROGRESS.md` with the schema below.
2. Run the validation command and record pass/fail counts in the file.
3. Commit all completed units of work to Git with an atomic, descriptive commit message.

---

### `notes/PROGRESS.md` — Required Outline

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

---

### `notes/DECISIONS.md` — Required Outline

---
updated: YYYY-MM-DD HH:MM
---

# Design Decisions

## YYYY-MM-DD: <Decision title>
- **Decision:** <what was chosen>
- **Reason:** <why>
- **Rejected alternatives:** <option> — <why rejected>
- **Active constraints:** <any constraints that must remain>

Add an entry for every significant architectural or design choice. One entry per decision; no need
for prose — bullet points only.

## Git Commits as Checkpoints
- Commit after every atomic unit of completed work (a passing test, a finished function, a merged
module — not just at the end of a session).
- Commit message format: <type>: <what> — <why if non-obvious> (e.g.,
fix: pagination 500 on empty set — guard added before slice).
- Never batch unrelated changes in a single commit.

## Context Reset Strategy
- Short tasks (< 30 min / < 60% window): No action needed — complete in-session.
- Long tasks (> 60% window): Clock out, then start a fresh session that clocks in from the
persistence files. Do not summarize-and-continue when context anxiety is a risk.

## Harness Initialization Reminder
- If the project has a notes/PROGRESS.md, you must read it before writing a single line of code.
- If neither notes/PROGRESS.md nor notes/DECISIONS.md exist yet, create them using the outlines
above and commit them as the first checkpoint before beginning the task.