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

## Language

Detect language: `PYTHONPATH=.claude/skills/ot python -m scripts.config detect --json`. All user-facing text MUST be in the detected language. Example text below is in English — translate it.

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

### Step 2: Check for previous runs & get input

- Check for previous runs: `python -m scripts.list_runs --json`
- If previous runs exist for this pipeline, AskUserQuestion:
  - "Start fresh" — create a new run from scratch (previous runs are kept)
  - "Resume from node N" — reuse previous results for earlier nodes, continue from node N
  - Show completed nodes from the latest run for context
- NOTE: "Start fresh" always creates a new run with a new ID. Previous runs are never deleted — they remain in runs/ or archive/. Make this clear in the option description so users know old runs are preserved.
- If "Resume from node N": ask which node number, save as `from_node`
- AskUserQuestion: "Provide input for the {first/starting} node:"
  - If resuming from node N and user says "use previous" or similar, skip input (script defaults to previous node's output)

### Step 3: Setup run

**IMPORTANT**: Write user input to temp file to avoid shell length limits.

```bash
# Fresh run:
PYTHONPATH=.claude/skills/ot python -m scripts.setup_run <pipeline.yaml> --input-file .o-team/tmp-input.md --json

# Resume from node N (uses previous run's outputs for nodes before N):
PYTHONPATH=.claude/skills/ot python -m scripts.setup_run <pipeline.yaml> --from <N> --json

# Resume from node N with custom input:
PYTHONPATH=.claude/skills/ot python -m scripts.setup_run <pipeline.yaml> --from <N> --input-file .o-team/tmp-input.md --json

# Resume from specific run:
PYTHONPATH=.claude/skills/ot python -m scripts.setup_run <pipeline.yaml> --from <N> --clone <run-id> --json
```

Save: `run_id`, `sandbox_path`, `nodes`, `total_nodes`, `start_from_index`

### Step 4: Execute nodes (LOOP)

For each node (index `start_from_index` to total_nodes-1, skipping COMPLETE nodes):

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
- Read `<sandbox_path>/<node_id>/output.md`, show preview (first 30 lines)
- AskUserQuestion: "Review the output:"
  - **View full output** — Read and display the ENTIRE output.md, then show this menu again
  - **Approve** — `complete_node`, continue
  - **Reject** — re-execute (4b)
  - **Edit** — first display the full output.md content, then AskUserQuestion "What changes would you like to make?", apply edits to output.md, show the updated content, then AskUserQuestion: Approve / Edit again
  - **Skip** — `complete_node --skip`, continue
  - **Abort** — stop

### Step 5: Complete

Show final output path.

#### 5a. Archive prompt
AskUserQuestion: "Name this run for archiving? (leave empty to skip)"
- If user provides a name:
  ```bash
  PYTHONPATH=.claude/skills/ot python -m scripts.archive_run <sandbox_path> --name "<user-input>" --json
  ```
  Show the new archived path from the result.
- If user skips (empty): continue without archiving.

#### 5b. Final
AskUserQuestion: "Show full output" / "Done"
