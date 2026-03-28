---
name: ot:run
description: Execute a pipeline
argument-hint: "[<pipeline-name>]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Run Pipeline

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

You are the **orchestrator**. You execute each node one at a time, report progress between nodes, and handle gates interactively.

## Flow

### Step 1: Select pipeline

- List all `.o-team/pipelines/*.yaml`
- If argument provided, pre-select that pipeline
- If only one pipeline exists, pre-select it
- AskUserQuestion: show numbered list, pre-selected as default. "Which pipeline to run?"
- Validate: `python -m scripts.validate_pipeline <path> --json`

### Step 2: Get initial input

- AskUserQuestion: "Provide initial input for the first node:"

### Step 3: Setup run

**IMPORTANT**: Write user input to temp file to avoid shell length limits.

```bash
# Write input to temp file, then:
PYTHONPATH=.claude/skills/ot python -m scripts.setup_run <pipeline.yaml> --input-file .o-team/tmp-input.md --json
```

Save: `run_id`, `sandbox_path`, `nodes`, `total_nodes`

### Step 4: Execute nodes (LOOP)

For each node (index 0 to total_nodes-1):

#### 4a. Announce
Tell user: `Node {i+1}/{total}: {node_id} ({team}) [{mode}]`

#### 4b. Execute (background)
```
PYTHONPATH=.claude/skills/ot python -m scripts.execute_node <sandbox_path> <node_index> --json
```
Use `run_in_background: true`.

#### 4c. Monitor
While waiting, check every 30-60s:
```
PYTHONPATH=.claude/skills/ot python -m scripts.check_status --live --json
```
Report: tool name, agent name, activity preview.

#### 4d. Handle result

**Error**: AskUserQuestion → Retry / Skip / Abort

**Success + auto**:
- `python -m scripts.complete_node <sandbox_path> <node_id> --json`
- Report result, continue to next node

**Success + gate**:
- Read `<sandbox_path>/<node_id>/output.md`, show preview (30 lines)
- AskUserQuestion: Approve / Reject / Edit / Skip / Abort
  - Approve → complete_node, continue
  - Reject → re-execute (4b)
  - Edit → modify output.md, then approve
  - Skip → `complete_node --skip`, continue
  - Abort → stop

### Step 5: Complete

Show final output path. AskUserQuestion: "Show full output" / "Done"
