---
name: ot:build
description: Build a named pipeline interactively by selecting and ordering teams
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Build Pipeline

## Language

Detect language: `PYTHONPATH=.claude/skills/ot python -m scripts.config detect --json`. All user-facing text MUST be in the detected language.

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

## Flow

**Use AskUserQuestion for EVERY user interaction step.**

**Step 1: List registered teams**
- Run `python -m scripts.registry list --json`
- Present numbered list with summaries and capabilities
- If no teams registered, tell user to register first (`/ot:reg add <path>`) and stop

**Step 2: Select teams**
- AskUserQuestion: "Select teams for this pipeline (enter numbers in execution order, e.g. 1,3,2)"

**Step 3: Set execution mode**
- Show default: auto for all except last (gate)
- AskUserQuestion: "Use defaults (auto -> ... -> gate)" / "Customize modes"

**Step 4: Name the pipeline**
- AskUserQuestion: "Pipeline name:"

**Step 5: Objective and first node prompt**
- AskUserQuestion: "What is the overall objective of this pipeline?"
- AskUserQuestion: "What should the first node do? (starting prompt)"

**Step 6: Auto-generate prompts**
- Read each team's CLAUDE.md from their team_path
- Generate prompts for all subsequent nodes based on objective, first node prompt, team capabilities, position
- Prompt guidelines:
  - Do NOT reference input.md or output.md (system handles this automatically)
  - Node 1: reference input contextually ("Based on the provided topic")
  - Subsequent nodes: reference previous step contextually ("Based on the previous analysis")
  - **Output format placement**: user-specified deliverable format (HTML, PDF, etc.) goes on the LAST node only. Intermediate nodes produce structured markdown.

**Step 7: Review prompts**
- Present complete pipeline with all prompts
- AskUserQuestion: "Confirm pipeline?" → Confirm / Modify / Cancel

**Step 8: Generate pipeline YAML**
- `python -m scripts.create_pipeline --name "<name>" --objective "<obj>" --nodes '<json>' --json`
