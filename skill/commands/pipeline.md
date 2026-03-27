---
name: o-team:pipeline
description: Manage pipelines — list, show, or remove
argument-hint: "list | show <name> | remove <name>"
allowed-tools:
  - Read
  - Bash
  - Glob
  - AskUserQuestion
---

# O-Team Pipeline Management

## Script Location

Find the o-team skill directory: look for `SKILL.md` in `.claude/skills/o-team/`. Run all Python scripts from that directory with `cwd` set to it.

## Actions

Parse the argument to determine the action. Default to `list` if no argument given.

### list (default)

1. List all `.o-team/pipelines/*.yaml` files
2. For each, read the YAML and show: name, node count, team sequence
3. Present as numbered list

### show <name>

1. Read `.o-team/pipelines/<name>.yaml`
2. Display full pipeline details: name, objective, each node (team, mode, prompt preview)

### remove <name>

1. Check `.o-team/pipelines/<name>.yaml` exists
2. Delete the file
3. Confirm removal
