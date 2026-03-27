---
name: o-team:runs
description: List run history with state, progress, and timestamps
allowed-tools:
  - Read
  - Bash
---

# O-Team Runs

## Script Location

Find the o-team skill directory: look for `SKILL.md` in `.claude/skills/o-team/`. Run all Python scripts from that directory with `cwd` set to it.

## Flow

1. Run `python -m scripts.list_runs --json`
2. Present as table with run ID, pipeline name, state, progress, timestamps
