---
name: ot:reg
description: Manage team registry — list, add, or remove teams
argument-hint: "[add <path> | rm <slug>]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Team Registry

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

## Actions

Parse the argument. Default to **list** if no argument.

### list (default)

1. Run `python -m scripts.registry list --json`
2. Present as table: slug, name, summary, capabilities, agent count

### add \<path\>

1. Run `python -m scripts.registry add <path> --json`
2. **Single team** (`mode: "single"`):
   - Read team's CLAUDE.md and .claude/agents/
   - Generate `summary` (one sentence) and `capabilities` (3-5 keywords)
   - `python -m scripts.registry update <team.slug> --summary "..." --capabilities "kw1,kw2,kw3" --json`
3. **Multi-team directory** (`mode: "multi"`):
   - Register ALL candidates: `python -m scripts.registry register-selected <path1> <path2> ... --json`
   - For each result, generate summary + capabilities and update **one at a time**:
     `python -m scripts.registry update <result.team.slug> --summary "..." --capabilities "kw1,kw2" --json`
   - Use slug from response (`result.team.slug`), NOT folder name

### rm \<slug\>

1. Run `python -m scripts.registry remove <slug> --json`
2. Confirm result
