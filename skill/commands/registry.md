---
name: ot:registry
description: "Alias for /ot:reg — manage team registry"
argument-hint: "add <path> | list | remove <slug>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

This command has a shorter alias: `/ot:reg`

Follow the exact same flow as `/ot:reg`. Parse argument as:
- `add <path>` → same as `/ot:reg add <path>`
- `list` or no argument → same as `/ot:reg` (list)
- `remove <slug>` → same as `/ot:reg rm <slug>`

Script: `PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json`

See `/ot:reg` for full documentation.
