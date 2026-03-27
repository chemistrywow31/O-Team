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

**Step 4: Execute (background)**
- Run pipeline in the **background** so you can report progress:
  ```
  PYTHONPATH=.claude/skills/o-team python -m scripts.run_pipeline <pipeline-yaml> --input "<input>" --json
  ```
  Use `run_in_background: true` for the Bash tool.
- Immediately tell user: "Pipeline started. I'll monitor progress and report updates."

**Step 5: Monitor progress**
While the pipeline runs in background, **periodically check and report status** to keep the user informed.

- Read the live status file to see real-time activity:
  ```
  PYTHONPATH=.claude/skills/o-team python -m scripts.check_status --live --json
  ```
- This returns: current node, phase (running/tool/agent), active tool name, agent name, text preview
- Report a concise status update to the user, e.g.:
  - "Node 1/3 (research-team): Agent 'Investigator Alpha' running — WebSearch"
  - "Node 1/3 (research-team): Tool Read — src/config.py"
  - "Node 2/3 (design-team): Writing output..."
- Check every **30-60 seconds** while waiting for the background task notification
- When you receive the background task completion notification, **stop monitoring** and proceed to Step 6

**Step 6: Handle result**
Read the pipeline result from the background task output.

- If state is **PAUSED** (gate node): go to Step 7
- If state is **ERROR**: go to Step 8
- If state is **COMPLETE**: go to Step 9

**Step 7: Handle gate pauses**
When state is PAUSED, show output preview then use AskUserQuestion:
- Read the gate node's output.md from the sandbox path
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
- After approve/reject/skip, resume pipeline:
  ```
  PYTHONPATH=.claude/skills/o-team python -m scripts.run_pipeline --resume <run-id> --json
  ```
  Run this in background again and return to Step 5 (monitor progress).

**Step 8: Handle errors**
When state is ERROR, show error then use AskUserQuestion:
- Options: "Retry" / "Skip" / "Abort"

**Step 9: Pipeline complete**
Show final output location, offer to display output.md
