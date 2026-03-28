---
name: o-team:status
description: "[Alias → /ot:status] Check run status"
argument-hint: "<run-id>"
allowed-tools:
  - Read
  - Bash
---

This command has a shorter alias: `/ot:status`

Follow the exact same flow as `/ot:status`.

Script: `PYTHONPATH=.claude/skills/o-team python -m scripts.<module> <args> --json`
