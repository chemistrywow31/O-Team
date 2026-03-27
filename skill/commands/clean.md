---
name: o-team:clean
description: Clean up run directories
argument-hint: "[run-id | --all | --state COMPLETE]"
allowed-tools:
  - Read
  - Bash
  - AskUserQuestion
---

# O-Team Clean

## Script Location

Find the o-team skill directory: look for `SKILL.md` in `.claude/skills/o-team/`. Run all Python scripts from that directory with `cwd` set to it.

## Flow

- Without argument: `python -m scripts.clean_runs --json` → show summary, ask what to clean
- With run-id: `python -m scripts.clean_runs <run-id> --json`
- With "all": `python -m scripts.clean_runs --all --json`
- With state: `python -m scripts.clean_runs --state COMPLETE --json`
