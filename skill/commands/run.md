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

**Use AskUserQuestion for user interaction steps.** Do NOT use free-form text conversation.

**Step 1: Locate pipeline**
- Look for `.o-team/pipelines/<pipeline-name>.yaml`
- If not found, try slugified version
- If still not found, list `.o-team/pipelines/` and use AskUserQuestion to let user pick

**Step 2: Validate pipeline**
- Run `PYTHONPATH=.claude/skills/o-team python -m scripts.validate_pipeline <path> --json`

**Step 3: Get initial input**
- Use AskUserQuestion:
  - Question: "Provide initial input for the first node:"

**Step 4: Execute**
- Run `PYTHONPATH=.claude/skills/o-team python -m scripts.run_pipeline <pipeline-yaml> --input "<input>" --json`
- The script handles sandbox creation, prompt assembly, stream-json parsing, and execution

**Step 5: Handle gate pauses**
When state is PAUSED, show output preview then use AskUserQuestion:
- Question: "Review node output. What would you like to do?"
- Options:
  - "Approve — accept and continue"
  - "Reject — discard and re-run this node"
  - "Edit — modify output.md then continue"
  - "Skip — skip this node"
  - "Abort — cancel entire pipeline"
- Apply:
  - Approve → `PYTHONPATH=.claude/skills/o-team python -m scripts.approve_node <run-id> <node-id> approve --json` then resume
  - Reject → `... reject --json` then resume
  - Edit → let user modify output.md, then approve
  - Skip → `... skip --json` then resume
  - Abort → `... abort --json`

**Step 6: Handle errors**
When state is ERROR, show error then use AskUserQuestion:
- Options: "Retry" / "Skip" / "Abort"

**Step 7: Pipeline complete**
Show final output location, offer to display output.md
