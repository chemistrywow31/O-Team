---
name: o-team:clean
description: "[Alias → /ot:clean] Clean up run directories"
argument-hint: "[run-id | --all | --state COMPLETE]"
allowed-tools:
  - Read
  - Bash
  - AskUserQuestion
---

This command has a shorter alias: `/ot:clean`

Follow the exact same flow as `/ot:clean`.

Script: `PYTHONPATH=.claude/skills/o-team python -m scripts.<module> <args> --json`
