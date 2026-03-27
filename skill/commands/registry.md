---
name: o-team:registry
description: Manage team registry — add, list, or remove teams
argument-hint: "add <path> | list | remove <slug>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# O-Team Registry

First-time in this session? Show: **O-Team | Agent Office**

## Script Location

Find the o-team skill directory: look for `SKILL.md` in `.claude/skills/o-team/`. Run all Python scripts from that directory with `cwd` set to it.

```
python -m scripts.<module_name> <args> --json
```

Always use `--json` and parse the result.

## Actions

Parse the argument to determine the action: `add <path>`, `list`, or `remove <slug>`.

### add <path>

1. Run `python -m scripts.registry add <path> --json`
2. **Single team mode** (path contains CLAUDE.md):
   - Script validates and registers the team
   - Read the team's CLAUDE.md and .claude/agents/ structure
   - Generate a `summary` (one sentence) and `capabilities` (3-5 keywords)
   - Update: `python -m scripts.registry update <slug> --summary "..." --capabilities "kw1,kw2,kw3" --json`
3. **Multi-team directory mode** (no CLAUDE.md):
   - Script scans subdirectories, returns candidates and warnings
   - Present ALL results — both valid candidates AND warnings
   - Ask which to register (all or select by number)
   - For selected: `python -m scripts.registry register-selected <path1> <path2> ... --json`
   - Generate summary + capabilities for each

### list

1. Run `python -m scripts.registry list --json`
2. Present as numbered list with slug, name, summary, capabilities, agent count

### remove <slug>

1. Run `python -m scripts.registry remove <slug> --json`
2. Confirm result
