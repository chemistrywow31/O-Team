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

Find the o-team skill directory (contains `SKILL.md`): `.claude/skills/o-team/`.

**IMPORTANT**: Run scripts from the **project root** (not the skill directory), using `PYTHONPATH`:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module_name> <args> --json
```

## Flow

- Without argument: `python -m scripts.clean_runs --json` → show summary, ask what to clean
- With run-id: `python -m scripts.clean_runs <run-id> --json`
- With "all": `python -m scripts.clean_runs --all --json`
- With state: `python -m scripts.clean_runs --state COMPLETE --json`
