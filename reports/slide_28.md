---
title: "Questions?"
slide: "28"
section: "Wrap-up"
date: "2026-05-31"
---

# Questions?

## Reference

| Resource | Location |
|----------|----------|
| Full usage docs | `python/README.md` |
| Source code | `python/easy_agent/` |
| Test suite | `python/tests/` |
| User settings | `~/.easy-agent/settings.json` |
| Skills directory | `~/.easy-agent/skills/` |
| Agents directory | `~/.easy-agent/agents/` |

## Quick Start

```bash
# Install
cd python && uv sync

# Run interactive mode
easy-agent

# Run in read-only plan mode
easy-agent --plan

# Run non-interactively (CI)
easy-agent --print "Summarise recent changes" --auto
```

## Contributing

- Custom tools: subclass `Tool`, register at bootstrap
- Custom skills: drop a `.md` in `~/.easy-agent/skills/`
- Bug reports / feature requests: open an issue in the repository

---

*Speaker notes: Leave time for questions. Common questions: "Can it run without macOS sandbox?" (yes — sandbox is macOS only, graceful no-op elsewhere). "Can it use non-Claude models?" (no — it's tightly coupled to the Anthropic SDK). "How do you resume sessions?" (--resume SESSION_ID from the status bar or session storage).*
