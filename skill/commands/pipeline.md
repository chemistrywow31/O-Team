---
name: ot:pipeline
description: "Alias for /ot:pipe — manage pipelines"
argument-hint: "list | show <name> | remove <name>"
allowed-tools:
  - Read
  - Bash
  - Glob
  - AskUserQuestion
---

This command has a shorter alias: `/ot:pipe`

Follow the exact same flow as `/ot:pipe`. Parse argument as:
- `list` or no argument → same as `/ot:pipe` (list)
- `show <name>` → same as `/ot:pipe show <name>`
- `remove <name>` → same as `/ot:pipe rm <name>`

Script: `PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json`

See `/ot:pipe` for full documentation.
