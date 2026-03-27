---
name: o-team:run
description: Execute a pipeline
argument-hint: "<pipeline-name>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# O-Team Run Pipeline

First-time in this session? Show: **O-Team | Agent Office**

## Script Location

Find the o-team skill directory (contains `SKILL.md`): `.claude/skills/o-team/`.

**IMPORTANT**: Run scripts from the **project root** (not the skill directory), using `PYTHONPATH`:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module_name> <args> --json
```

## Flow

**Step 1: Locate pipeline**
- Look for `.o-team/pipelines/<pipeline-name>.yaml`
- If not found, try slugified version
- If still not found, list `.o-team/pipelines/` and suggest matches

**Step 2: Validate pipeline**
- Run `python -m scripts.validate_pipeline <path> --json`

**Step 3: Get initial input**
- Ask user for initial input (text, file path, or "none")

**Step 4: Execute**
- Run `python -m scripts.run_pipeline <pipeline-yaml> --input "<input>" --json`
- The script handles sandbox creation, prompt assembly, stream-json parsing, and execution

**Step 5: Handle gate pauses**
When state is PAUSED, ask user:
- **approve** → `python -m scripts.approve_node <run-id> <node-id> approve --json` then `python -m scripts.run_pipeline --resume <run-id> --json`
- **reject** → `python -m scripts.approve_node <run-id> <node-id> reject --json` then resume
- **edit** → let user modify output.md, then approve
- **skip** → `python -m scripts.approve_node <run-id> <node-id> skip --json` then resume
- **abort** → `python -m scripts.approve_node <run-id> <node-id> abort --json`

**Step 6: Handle errors**
When state is ERROR, show error and ask: retry, skip, or abort

**Step 7: Pipeline complete**
Show final output location, offer to display output.md
