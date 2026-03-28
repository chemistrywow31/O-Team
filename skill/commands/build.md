---
name: o-team:build
description: "[Alias → /ot:build] Build a named pipeline"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

This command has a shorter alias: `/ot:build`

Follow the exact same flow as `/ot:build`.

Script: `PYTHONPATH=.claude/skills/o-team python -m scripts.<module> <args> --json`

See `/ot:build` for full documentation.
