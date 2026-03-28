---
name: o-team:run
description: "[Alias → /ot:run] Execute a pipeline"
argument-hint: "<pipeline-name>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

This command has a shorter alias: `/ot:run`

Follow the exact same flow as `/ot:run`.

Script: `PYTHONPATH=.claude/skills/o-team python -m scripts.<module> <args> --json`

See `/ot:run` for full documentation.
