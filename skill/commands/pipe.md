---
name: ot:pipe
description: Manage pipelines — list, show, or remove
argument-hint: "[show <name> | rm <name>]"
allowed-tools:
  - Read
  - Bash
  - Glob
  - AskUserQuestion
---

# Pipeline Management

## Script

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module> <args> --json
```

## Actions

Parse the argument. Default to **list** if no argument.

### list (default)

1. List all `.o-team/pipelines/*.yaml` files
2. For each, read YAML and show: name, node count, team sequence
3. Present as numbered list

### show \<name\>

1. Read `.o-team/pipelines/<name>.yaml`
2. Display: name, objective, each node (team, mode, prompt preview)

### rm \<name\>

1. Check `.o-team/pipelines/<name>.yaml` exists
2. Delete the file
3. Confirm removal
