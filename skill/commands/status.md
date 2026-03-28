---
name: ot:status
description: Check run status — live or by run-id
argument-hint: "[<run-id> | live]"
allowed-tools:
  - Read
  - Bash
---

# Run Status

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

## Actions

- No argument or `live`: `python -m scripts.check_status --live --json`
- With run-id: `python -m scripts.check_status <run-id> --json`

Present node states with icons: PENDING, RUNNING, COMPLETE, ERROR, PAUSED, SKIPPED.
