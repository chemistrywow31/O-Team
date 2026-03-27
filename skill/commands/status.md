---
name: o-team:status
description: Check run status and per-node progress
argument-hint: "<run-id>"
allowed-tools:
  - Read
  - Bash
---

# O-Team Status

## Script Location

Find the o-team skill directory: look for `SKILL.md` in `.claude/skills/o-team/`. Run all Python scripts from that directory with `cwd` set to it.

## Flow

1. Run `python -m scripts.check_status <run-id> --json`
2. Present node states with icons
