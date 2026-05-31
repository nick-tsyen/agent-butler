---
title: "What Is Agent Butler?"
slide: "02"
section: "Introduction"
date: "2026-05-31"
---

# What Is Agent Butler?

Agent Butler is an interactive multi-turn AI coding agent. You type a question; Claude streams a response; if it needs to act, it calls tools; it loops until done.

---

**Capabilities**

- Interactive multi-turn REPL
- File read/write and shell execution (sandboxed)
- Code search (Grep, Glob)
- Sub-agent delegation
- MCP (Model Context Protocol) tool servers
- Skills: reusable Markdown-defined workflows
- Permission system with three modes
- Persistent tasks, sessions, and memory

---

**Scale**

> 9,100 lines, 85+ files, fully async, Pydantic-typed throughout

---

*Speaker notes: Think of Agent Butler as a local Claude Code clone. It wraps the Anthropic API in a full agentic harness: tool execution, sandboxing, permissions, memory, and sub-agents. Every capability listed here maps to a distinct subsystem in the codebase, each of which will be covered in later slides.*
