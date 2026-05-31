---
updated: YYYY-MM-DD HH:MM
---

# Design Decisions

A lightweight log of *why* the code is the way it is. Read this at the start of every session so you
do not reverse or "optimize away" a deliberate choice. Add one entry per significant architectural
or design decision — bullet points only, no prose.

## YYYY-MM-DD: <Decision title>

- **Decision:** <what was chosen>
- **Reason:** <why>
- **Rejected alternatives:** <option> — <why rejected>
- **Active constraints:** <any constraint that must remain true>

## 2024-01-15: Use Redis for user-preferences caching (example)

- **Decision:** Cache user preferences in Redis.
- **Reason:** High read frequency (every API call), small data size.
- **Rejected alternatives:** PostgreSQL materialized view — high change frequency makes maintenance
  cost not worthwhile.
- **Active constraints:** Cache TTL of 5 minutes; active invalidation on write.
