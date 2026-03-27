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

Find the o-team skill directory (contains `SKILL.md`): `.claude/skills/o-team/`.

**IMPORTANT**: Run scripts from the **project root** (not the skill directory), using `PYTHONPATH` to locate the scripts module:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module_name> <args> --json
```

This ensures `.o-team/` data (pipelines, runs) is created in the project root, not inside the skill directory. Always use `--json` and parse the result.

## Actions

Parse the argument to determine the action: `add <path>`, `list`, or `remove <slug>`.

### add <path>

1. Run `python -m scripts.registry add <path> --json`
2. **Single team mode** (response has `"mode": "single"`):
   - The response contains `team.slug` — use THIS slug for all subsequent commands
   - Read the team's CLAUDE.md and .claude/agents/ structure
   - Generate a `summary` (one sentence) and `capabilities` (3-5 keywords)
   - Update using the slug FROM THE RESPONSE: `python -m scripts.registry update <team.slug> --summary "..." --capabilities "kw1,kw2,kw3" --json`
3. **Multi-team directory mode** (response has `"mode": "multi"`):
   - The response contains `candidates` (valid teams) and `warnings` (invalid subdirs)
   - **Register ALL candidates automatically** — do NOT ask the user to select
   - Run `python -m scripts.registry register-selected <path1> <path2> ... --json` with all candidate paths
   - The response contains `results` array — each successful result has `result.team.slug`
   - **IMPORTANT**: Use the slug from each result (`result.team.slug`), NOT the folder name. Slugs are derived from the CLAUDE.md title, not the folder name.
   - For each successfully registered team, generate summary + capabilities and update **one at a time** (not in parallel):
     `python -m scripts.registry update <result.team.slug> --summary "..." --capabilities "kw1,kw2" --json`
   - Show warnings for invalid subdirectories but continue

### list

1. Run `python -m scripts.registry list --json`
2. Present as numbered list with slug, name, summary, capabilities, agent count

### remove <slug>

1. Run `python -m scripts.registry remove <slug> --json`
2. Confirm result
