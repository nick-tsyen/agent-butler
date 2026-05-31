---
title: "Permission System: Modes, Rules & Hierarchy"
slide: "16"
section: "Tool System"
date: "2026-05-31"
---

# Permission System: Modes, Rules & Hierarchy

**Three permission modes**

| Mode | Behaviour |
|------|-----------|
| `default` | Read-only tools auto-allowed; writes and shell require inline user confirmation |
| `plan` | Only Read, Grep, Glob (and read-only Bash) allowed; all mutations hard-blocked |
| `auto` | All operations auto-approved — for scripting and CI use |

---

**Rule syntax** (`settings.json`)

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Bash(npm test *)",
      "mcp__filesystem*"
    ],
    "deny": [
      "Bash(rm -rf *)"
    ]
  }
}
```

Rule matching forms:

| Form | Example | Meaning |
|------|---------|---------|
| Exact tool name | `"Read"` | Match this tool only |
| Parameterised glob | `"Bash(npm test *)"` | Match Bash calls whose command matches the glob |
| Namespace wildcard | `"mcp__filesystem*"` | Match all tools in the MCP server namespace |

---

**Permission decision flow**

```
tool.call() requested
  -> check_permission(tool, input)
       -> match against deny rules   -> deny if matched
       -> match against allow rules  -> allow if matched
       -> if mode == "auto"          -> allow
       -> if mode == "plan"
            and not read-only        -> deny
       -> else                       -> prompt user
               -> user chooses:
                    allow_once
                    allow_always
                    deny
```

---

**Load hierarchy** (later overrides earlier)

1. User scope: `~/.agent-butler/settings.json`
2. Project scope: `./.agent-butler/settings.json`
3. Session rules: `allow_always` decisions from current session

Source: `permissions/permissions.py` (~300 lines)

---

*Speaker notes: The permission system is intentionally layered so that project-specific rules can override user defaults. For example, a project might allow `Bash(npm *)` without requiring the user to approve it globally. The `allow_always` session rule persists only for the current session.*
