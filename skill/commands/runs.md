---
name: o-team:runs
description: List run history with state, progress, and timestamps
allowed-tools:
  - Read
  - Bash
---

# O-Team Runs

## Script Location

Find the o-team skill directory (contains `SKILL.md`): `.claude/skills/o-team/`.

**IMPORTANT**: Run scripts from the **project root** (not the skill directory), using `PYTHONPATH`:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module_name> <args> --json
```

## Flow

1. Run `python -m scripts.list_runs --json`
2. Present as table with run ID, pipeline name, state, progress, timestamps
