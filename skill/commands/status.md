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

Find the o-team skill directory (contains `SKILL.md`): `.claude/skills/o-team/`.

**IMPORTANT**: Run scripts from the **project root** (not the skill directory), using `PYTHONPATH`:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module_name> <args> --json
```

## Flow

1. Run `python -m scripts.check_status <run-id> --json`
2. Present node states with icons
