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

You are the **orchestrator**. You execute each node one at a time, report progress between nodes, and handle gates interactively. This keeps you alive and visible to the user throughout the pipeline.

---

### Step 1: Select pipeline

- List all pipelines: `ls .o-team/pipelines/*.yaml`
- If an argument was provided (e.g. `/o-team:run my-pipeline`), pre-select that one
- If only one pipeline exists, pre-select it
- Use AskUserQuestion to confirm or choose:
  - Show numbered list of all available pipelines
  - Pre-selected pipeline should be marked as default
  - Question: "Which pipeline to run?"
- Validate selected pipeline: `PYTHONPATH=.claude/skills/o-team python -m scripts.validate_pipeline <path> --json`

### Step 2: Get initial input

- Use AskUserQuestion:
  - Question: "Provide initial input for the first node:"

### Step 3: Setup run

Create the sandbox (no execution yet).

**IMPORTANT**: Always write the user input to a temp file first, then pass `--input-file`. Never pass long text via `--input` (shell argument length limits).

```bash
# 1. Write user input to temp file
Write the input content to .o-team/tmp-input.md

# 2. Setup run with file input
PYTHONPATH=.claude/skills/o-team python -m scripts.setup_run <pipeline-yaml> --input-file .o-team/tmp-input.md --json
```

Save from the result:
- `run_id`
- `sandbox_path`
- `nodes` array (each has `id`, `team`, `mode`)
- `total_nodes`

Tell user: "Pipeline **{pipeline_name}** ready — {total_nodes} nodes. Starting execution."

### Step 4: Execute nodes (LOOP)

For each node in the `nodes` array, from index 0 to total_nodes-1:

#### 4a. Announce

Tell user:
```
▶ Node {index+1}/{total}: {node_id} ({team}) [{mode}]
```

#### 4b. Execute node (background)

Run in background (`run_in_background: true`):

```
PYTHONPATH=.claude/skills/o-team python -m scripts.execute_node <sandbox_path> <node_index> --json
```

#### 4c. Monitor progress

While waiting for the background task to complete, **periodically check and report status**:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.check_status --live --json
```

- Report a concise status update to the user based on the `phase`, `tool`, `agent`, `preview` fields
- Examples:
  - "🔧 Tool: WebSearch"
  - "🤖 Agent: Investigator Alpha — researching market data"
  - "✍️ Writing output..."
- Check every **30-60 seconds**
- When you receive the background task completion notification, **stop monitoring** and proceed to 4d

#### 4d. Handle result

Read the result from the background task output (JSON).

**If error** (`success: false`):
- Show: "❌ Node '{node_id}' failed (exit {exit_code})"
- Use AskUserQuestion:
  - Options: "Retry" / "Skip" / "Abort"
  - Retry → go back to 4b for this node
  - Skip → run `python -m scripts.complete_node <sandbox_path> <node_id> --skip --json`, continue to next node
  - Abort → stop pipeline

**If success + auto mode**:
- Run `PYTHONPATH=.claude/skills/o-team python -m scripts.complete_node <sandbox_path> <node_id> --json`
- Show: "✅ Node '{node_id}' complete ({duration}s, ${cost}). → Moving to {next_node_id}"
- Continue to next node

**If success + gate mode**:
- Read the node's output.md: `<sandbox_path>/<node_id>/output.md`
- Show a preview of the output (first 30 lines)
- Use AskUserQuestion:
  - Question: "Review the output. What would you like to do?"
  - Options:
    - "Approve — accept and continue"
    - "Reject — discard and re-run this node"
    - "Edit — modify output before continuing"
    - "Skip — skip this node"
    - "Abort — cancel pipeline"
  - Approve → run `python -m scripts.complete_node <sandbox_path> <node_id> --json`, continue
  - Reject → go back to 4b (re-execute this node)
  - Edit → let user describe changes, apply edits to output.md, then treat as Approve
  - Skip → run `python -m scripts.complete_node <sandbox_path> <node_id> --skip --json`, continue
  - Abort → stop pipeline

### Step 5: Pipeline complete

When all nodes are done:
- Show: "🏁 Pipeline '{pipeline_name}' complete"
- Show final output path from the last complete_node result
- Use AskUserQuestion:
  - Question: "What would you like to do?"
  - Options: "Show full output" / "Done"
  - If "Show full output": Read and display the final output.md
