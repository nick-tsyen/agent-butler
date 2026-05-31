# Evaluator Rubric

Use this rubric after implementation and before final acceptance.

> **Worker–checker separation:** the agent that generated the work must **not** be the one that
> scores it. Models are systematically overconfident and will talk themselves into approving their
> own output — use an independent evaluator (a separate agent invocation or a hardcoded test suite)
> as the gatekeeper.

| Category | Question | Score (0-2) | Notes |
| --- | --- | --- | --- |
| Correctness | Does the implemented behavior match the requested feature? |  |  |
| Verification | Did the required checks actually run, with evidence? |  |  |
| Architecture compliance | Does the change respect the layer boundaries in `CONSTRAINTS.md`? |  |  |
| Scope discipline | Did the session stay inside the chosen feature scope? |  |  |
| Reliability | Does the result survive restart or rerun without repair? |  |  |
| Maintainability | Is the code and documentation clear enough for the next session? |  |  |
| Handoff readiness | Can a fresh session continue work from repo artifacts only? |  |  |

## Verdict

- Accept
- Revise
- Block

## Required Follow-Up

- Missing evidence:
- Required fixes:
- Next review trigger:

---

**Tuning note — the evaluator needs calibration.** Out of the box, agents are poor self-judges:
they identify issues, then talk themselves into approving. Iterate:

1. Run the evaluator on a completed sprint.
2. Compare its scores against your own human judgment.
3. Where they diverge, make the pass/fail criteria for that dimension more specific.
4. Re-run and check alignment.
5. Repeat until the evaluator consistently matches human review.

Plan for 3–5 tuning rounds; record each change so you can track what improved alignment.
