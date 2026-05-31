---
title: "Skills: Reusable Markdown Workflows"
slide: "18"
section: "Extensions & Integrations"
date: "2026-05-31"
---

# Skills: Reusable Markdown Workflows

A skill is a `.md` file with YAML frontmatter that encodes a reusable workflow as a system-prompt fragment.

**Example skill file**

```markdown
---
name: review
description: Perform a thorough code review
allowedTools: [Read, Grep, Glob]
budget: 3000
paths: [src/*, tests/*]
---

You are an expert code reviewer. Focus on correctness,
security, and maintainability. Be specific about file
locations and line numbers in your feedback.
```

---

**Frontmatter fields**

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | Yes | Invocation name (used by `SkillTool`) |
| `description` | Yes | Shown in system prompt so Claude knows when to use it |
| `allowedTools` | No | Restrict which tools the skill can use |
| `budget` | No | Max tokens for skill context |
| `paths` | No | Conditional activation path patterns |

---

**Two activation modes**

```
Dynamic  (no paths field)
  -> always injected into system prompt
  -> globally available in every session

Conditional  (has paths field)
  -> activated only when CWD matches a path pattern
  -> useful for project-specific workflows
     e.g. paths: [src/backend/*]  ->  only active inside backend dir
```

---

**Load order**

```
~/.agent-butler/skills/      (user scope)
./.agent-butler/skills/      (project scope)

Project files override user files of the same name.
```

**Source:** `services/skills/registry.py`, `services/skills/load_skills_dir.py`, `services/skills/parse_frontmatter.py`

---

*Speaker notes: Skills are the "prompt engineering" layer. They let teams encode workflows — code review, security audit, test generation — as versioned markdown files that live alongside the code. No Python required to add a new skill.*
