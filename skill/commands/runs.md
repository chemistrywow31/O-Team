---
name: ot:runs
description: List run history
allowed-tools:
  - Read
  - Bash
---

# Run History

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

## Flow

1. Run `python -m scripts.list_runs --json`
2. Present as table: run ID, pipeline name, state, progress, timestamps
