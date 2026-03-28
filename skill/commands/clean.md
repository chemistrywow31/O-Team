---
name: ot:clean
description: Clean up run directories
argument-hint: "[<run-id> | --all | --state COMPLETE]"
allowed-tools:
  - Read
  - Bash
  - AskUserQuestion
---

# Clean Runs

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

## Actions

- No argument: `python -m scripts.clean_runs --json` → show summary, ask what to clean
- With run-id: `python -m scripts.clean_runs <run-id> --json`
- With `--all`: `python -m scripts.clean_runs --all --json`
- With `--state`: `python -m scripts.clean_runs --state <STATE> --json`
