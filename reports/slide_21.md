---
title: "Sandbox: macOS sandbox-exec Integration"
slide: "21"
section: "Platform Services"
date: "2026-05-31"
---

# Sandbox: macOS `sandbox-exec` Integration

**Platform availability**

| Platform | Status | Notes |
|----------|--------|-------|
| macOS | Auto-enabled | Uses `sandbox-exec` binary, part of macOS |
| Linux | No-op | Sandbox layer bypassed |
| Windows | No-op | Sandbox layer bypassed |

Detection: `sandbox/availability.py`

---

**Call chain**

```
Bash tool call
  -> sandbox/should_use.py       (gate: is this command sandboxable?)
       -> sandbox/split_command.py    (split && / || compounds)
            -> sandbox/build_profile.py   (compose SBPL profile)
                 -> sandbox/wrap.py        (compile + wrap)
```

Wrapped command issued to the OS:

```bash
/usr/bin/sandbox-exec -p '<compiled-profile>' /bin/bash -lc '<command>'
```

---

**Example SBPL profile** (simplified)

```scheme
(version 1)
(deny default)
(allow process-exec)
(allow file-read*  (subpath "/Users/nick/project"))
(allow file-write* (subpath "/Users/nick/project"))
(deny  file-write* (subpath "/Users/nick/project/.git"))
(deny  network-outbound)
```

SBPL (Sandbox Profile Language) is a Scheme-like profile language interpreted by the macOS kernel.

---

**Profile composition — four rule sets**

| Rule set | Purpose |
|----------|---------|
| `allow_read` | Paths Claude may read |
| `allow_write` | Paths Claude may write |
| `deny_write` | Specific write overrides (e.g., `.git`) |
| Network | Allowed outbound domains, or full deny |

`sandbox/violations.py` monitors stderr for sandbox violation messages and logs them for audit.

---

**Defence-in-depth relationship**

```
Permission system          (application layer)
  -> decides whether Claude should call the tool

Sandbox (kernel layer)
  -> enforces file/network limits on what the process can do
  -> kernel blocks writes outside allowed paths
     even if Claude calls rm -rf /
```

---

*Speaker notes: `sandbox-exec` is a built-in macOS kernel feature. SBPL is a Scheme-like profile language. Using it means shell commands are kernel-enforced — even if Claude calls `rm -rf /`, the kernel will block writes outside allowed paths. It is a defence-in-depth measure, not a replacement for the permission system.*
