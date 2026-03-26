---
name: O-Team Pipeline Orchestrator
description: Orchestrate multi-team AI agent pipelines via CLI. Use when user wants to register agent teams, build named pipelines with ordered team sequences, or run pipelines that execute each team in isolated context with handoff files. Triggers on /o-team commands or mentions of pipeline, team orchestration, multi-team workflow.
---

# O-Team Pipeline Orchestrator

## Purpose

Enable users to register A-Team generated agent teams, build named execution pipelines by selecting and ordering teams, and run pipelines where each node operates in isolated context with its own team identity. Teams collaborate exclusively through handoff files (input.md / output.md).

## Commands

| Command | Trigger |
|---------|---------|
| `/o-team:registry add <path>` | Register team folder(s) |
| `/o-team:registry list` | List registered teams |
| `/o-team:registry remove <slug>` | Remove a registered team |
| `/o-team:build` | Build a named pipeline interactively |
| `/o-team:run <pipeline-name>` | Execute a pipeline |
| `/o-team:status <run-id>` | Check run status |
| `/o-team:runs` | List run history |
| `/o-team:clean [run-id]` | Clean up run directories |

## Script Location

All scripts are in the `scripts/` directory relative to this SKILL.md. Invoke with:

```
python -m scripts.<module_name> <args> --json
```

The `--json` flag produces machine-readable output. Always use `--json` and parse the result to present to the user.

Set `cwd` to the directory containing this SKILL.md (the o-team skill root) when invoking scripts via `python -m`.

---

## /o-team:registry add <path>

### Flow

1. Run `python -m scripts.registry add <path> --json`
2. Parse the JSON result. Two modes:

**Single team mode** (path contains CLAUDE.md):
- Script validates and registers the team
- If successful, read the team's CLAUDE.md and .claude/agents/ structure
- Generate a `summary` (one sentence describing the team's purpose) and `capabilities` (list of 3-5 keywords)
- Update the registry entry: `python -m scripts.registry update <slug> --summary "..." --capabilities "kw1,kw2,kw3" --json`
- Present the result to the user

**Multi-team directory mode** (path has no CLAUDE.md):
- Script scans subdirectories, returns candidates (valid teams) and warnings (subdirectories without CLAUDE.md)
- Present ALL results to the user — both valid candidates and warnings
- Warnings for subdirectories without CLAUDE.md MUST be shown (not silently skipped)
- Ask the user which candidates to register (all or select by number)
- For selected teams, run `python -m scripts.registry register-selected <path1> <path2> ... --json`
- For each registered team, read its CLAUDE.md and generate summary + capabilities as above

### Presentation Format

```
✅ team-name
   CLAUDE.md ✓  .claude/ ✓  Agents: N  Skills: N
   摘要: {AI-generated summary}

⚠️ subdirectory-name/
   無 CLAUDE.md，不是合法團隊
```

---

## /o-team:registry list

1. Run `python -m scripts.registry list --json`
2. Present as numbered list with slug, name, summary, capabilities, agent count

---

## /o-team:registry remove <slug>

1. Run `python -m scripts.registry remove <slug> --json`
2. Confirm result to user

---

## /o-team:build

### Flow

**Step 1: List registered teams**
- Run `python -m scripts.registry list --json`
- Present numbered list with summaries and capabilities
- If no teams registered, tell user to register first

**Step 2: Select and order**
- Ask user to select teams by number, in execution order (comma-separated)
- Example: "1,3,2" means team 1 first, then team 3, then team 2
- Confirm the order back to the user

**Step 3: Set execution mode per node**
- For each selected team, ask: auto or gate?
- auto = run and proceed without stopping
- gate = run, pause for user review before proceeding
- Default: gate for the last node, auto for others (suggest this default)

**Step 4: Name the pipeline**
- Ask user for a pipeline name
- This becomes both the display name and the YAML filename (slugified)

**Step 5: Get objective and first node prompt**
- Ask user: "What is the overall objective of this pipeline?"
- Ask user: "What should the first node do? (this is the starting prompt)"

**Step 6: Auto-generate prompts for remaining nodes**
- Read each team's CLAUDE.md file (from the team_path in registry)
- Based on:
  - The pipeline objective
  - The first node's prompt
  - Each team's capabilities and CLAUDE.md content
  - The position in the pipeline (what comes before, what comes after)
  - The handoff relationship (previous team's likely output → this team's expected input)
- Generate a specific, actionable prompt for each subsequent node
- Each prompt must:
  - Reference input.md as the source of context from the previous step
  - State clearly what deliverable to produce
  - Instruct to write the primary deliverable to output.md
  - Be concise but specific (3-8 sentences)

**Step 7: Present all prompts for confirmation**
- Show the complete pipeline with all prompts
- Ask user to confirm or modify specific nodes by number
- If user wants to modify, update that node's prompt and re-present

**Step 8: Generate pipeline YAML**
- Assemble the nodes JSON array:
  ```json
  [
    {"team": "slug", "mode": "auto", "prompt": "..."},
    {"team": "slug", "mode": "gate", "prompt": "..."}
  ]
  ```
- Run `python -m scripts.create_pipeline --name "<name>" --objective "<objective>" --nodes '<json>' --json`
- Present the result with file path

### Presentation Format for Step 7

```
Pipeline: tech-spec-pipeline
Objective: {objective}

  Node 1 — research-team [auto ⚡]
  Prompt: {prompt text}

  Node 2 — design-team [gate ⏸]
  Prompt: {prompt text}

  Node 3 — writing-team [auto ⚡]
  Prompt: {prompt text}

確認？(y / 修改節點編號)
```

---

## /o-team:run <pipeline-name>

### Flow

**Step 1: Locate pipeline**
- Look for `.o-team/pipelines/<pipeline-name>.yaml`
- If not found, try `.o-team/pipelines/<pipeline-name-slugified>.yaml`
- If still not found, run `ls .o-team/pipelines/` and suggest matches

**Step 2: Validate pipeline**
- Run `python -m scripts.validate_pipeline <path> --json`
- If invalid, show issues and stop

**Step 3: Get initial input**
- Ask user: "Provide initial input for the first node:"
  - User can type text directly
  - User can provide a file path (will be copied as input.md)
  - User can say "none" or "skip" for empty input

**Step 4: Execute**
- Run `python -m scripts.run_pipeline <pipeline-yaml> --input "<input>" --json`
- The script handles:
  - Creating UUID sandbox
  - Copying team configs into office folders
  - Assembling prompts
  - Spawning independent claude CLI processes
  - Streaming output to terminal
  - Auto-proceeding or pausing at gates

**Step 5: Handle gate pauses**
- When the script exits with state PAUSED, present the output preview
- Ask user for action:
  - **approve** — accept and continue
  - **reject** — discard and re-run this node
  - **edit** — let user modify the output.md, then approve
  - **skip** — skip this node, pass input through to next
  - **abort** — cancel the entire pipeline
- For approve: run `python -m scripts.approve_node <run-id> <node-id> approve --json`, then `python -m scripts.run_pipeline --resume <run-id> --json`
- For reject: run `python -m scripts.approve_node <run-id> <node-id> reject --json`, then `python -m scripts.run_pipeline --resume <run-id> --json`
- For edit: let user modify the file at `.o-team/runs/<run-id>/<node-id>/output.md`, then approve
- For skip: run `python -m scripts.approve_node <run-id> <node-id> skip --json`, then resume
- For abort: run `python -m scripts.approve_node <run-id> <node-id> abort --json`

**Step 6: Handle errors**
- When the script exits with state ERROR, show the error and log excerpt
- Ask user: retry, skip, or abort
- Same approve_node flow as above

**Step 7: Pipeline complete**
- Show final output location
- Offer to read and display the final output.md

---

## /o-team:status <run-id>

1. Run `python -m scripts.check_status <run-id> --json`
2. Present node states with icons

---

## /o-team:runs

1. Run `python -m scripts.list_runs --json`
2. Present as table with run ID, pipeline name, state, progress, timestamps

---

## /o-team:clean [run-id]

- Without run-id: run `python -m scripts.clean_runs --json` to show summary, then ask user what to clean
- With run-id: run `python -m scripts.clean_runs <run-id> --json`
- With "all": run `python -m scripts.clean_runs --all --json`
- With state filter: run `python -m scripts.clean_runs --state COMPLETE --json`

---

## Key Architecture Concepts

### Independent Context Per Node

Each pipeline node spawns a **separate `claude` CLI process**. The orchestrating Claude Code session (running this skill) is the meta-layer. Each worker process:
- Starts with a fresh context window
- Loads its own team's CLAUDE.md and .claude/ configuration
- Has no knowledge of other nodes or the overall pipeline
- Receives upstream information only through input.md
- Produces output.md as its deliverable

### Office Folder Structure

Each node's office folder is a complete, self-contained team environment:
```
{run-id}/{node-id}/
├── CLAUDE.md        ← copied from team
├── .claude/         ← copied from team
├── input.md         ← handoff from previous node
├── output.md        ← this node's deliverable
├── prompt.md        ← assembled prompt (audit trail)
└── run.log          ← CLI output log
```

### Artifact Flow

```
Node 1: reads input.md → produces output.md
         ↓ (orchestrator copies output → next input)
Node 2: reads input.md → produces output.md
         ↓
Node 3: reads input.md → produces output.md (final deliverable)
```

### Storage

- Global registry: `~/.o-team/registry.json`
- Project pipelines: `.o-team/pipelines/*.yaml` (can be git committed)
- Project runs: `.o-team/runs/{uuid}/` (gitignored)
