# Clean State Checklist

Run through this before ending **every** session. Session completion = the task passes verification
AND all five dimensions below hold. Missing any one means the session is not done.

- [ ] **Build passes** (e.g. `npm run build` / `make build`).
- [ ] **Tests pass** — the standard verification path runs green.
- [ ] **Progress recorded** — `claude-progress.md` updated (state, test counts, numbered Next Steps);
      `decisions.md` updated if a design choice was made.
- [ ] **Feature state accurate** — `feature_list.json` reflects what is actually passing versus
      unverified (no false `passing` entries).
- [ ] **Artifact hygiene** — no debug code or slop left behind: `console.log`, `debugger`, stray
      `TODO` markers, temporary logs, scratch files.
- [ ] **Startup path works** — the standard startup path (`./init.sh`) still runs; the next session
      can continue without manual repair.
