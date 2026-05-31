# Quality Document

A quality snapshot for each product domain and architectural layer. Both agents and humans can use this document to quickly understand where the codebase is strong and where it needs work.

**Update cadence:** After each significant session, or before starting a new phase of work.

**Grading scale:**

- **A**: All verification passing, clean architecture, agent-legible, stable tests
- **B**: Verification passing, mostly clean, minor gaps in legibility or test coverage
- **C**: Partially working, known gaps, some code areas hard for agents to understand
- **D**: Not working, or major structural issues

---

## Product Domains

| Domain | Grade | Verification | Agent Legibility | Test Stability | Key Gaps | Last Updated |
|--------|-------|-------------|-----------------|---------------|----------|-------------|
| Document Import | - | - | - | - | - | - |
| Document Management | - | - | - | - | - | - |
| Document Indexing | - | - | - | - | - | - |
| Q&A Flow | - | - | - | - | - | - |
| Grounded Answers | - | - | - | - | - | - |

## Architectural Layers

| Layer | Grade | Boundary Enforcement | Agent Legibility | Key Gaps | Last Updated |
|-------|-------|---------------------|-----------------|----------|-------------|
| Main Process | - | - | - | - | - |
| Preload | - | - | - | - | - |
| Renderer | - | - | - | - | - |
| Services | - | - | - | - | - |

## Change History

### YYYY-MM-DD

- Changes:
- Domains promoted:
- Domains demoted:
- New gaps identified:
- Gaps closed:

---

## Harness Simplification

Every harness component encodes an assumption about what the model *cannot* do on its own. As models
improve, those assumptions go stale and the component becomes overhead that can throttle execution.
Use this quality document to decide what to prune. Run roughly **monthly**:

1. Take a quality-document snapshot (the grades above).
2. Temporarily disable one harness component (e.g. a sprint-splitting step, a rigid sub-task gate).
3. Run the benchmark task suite.
4. Take another snapshot.
5. Compare — if grades did not drop, the component was overhead: **remove it permanently.** If they
   dropped, restore it (or replace it with a lighter alternative).

> The interesting combinations in a harness do not shrink as models improve — they *shift*. Keep
> finding the next valuable one rather than accumulating dead scaffolding.

