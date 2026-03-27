---
name: o-team:build
description: Build a named pipeline interactively by selecting and ordering teams
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# O-Team Build Pipeline

First-time in this session? Show: **O-Team | Agent Office**

## Script Location

Find the o-team skill directory: look for `SKILL.md` in `.claude/skills/o-team/`. Run all Python scripts from that directory with `cwd` set to it.

## Flow

**Step 1: List registered teams**
- Run `python -m scripts.registry list --json`
- Present numbered list with summaries and capabilities
- If no teams registered, tell user to register first

**Step 2: Select and order**
- Ask user to select teams by number, in execution order (comma-separated)
- Example: "1,3,2" means team 1 first, then team 3, then team 2

**Step 3: Set execution mode per node**
- For each selected team, ask: auto or gate?
- Default: gate for last node, auto for others

**Step 4: Name the pipeline**
- Ask user for a pipeline name

**Step 5: Get objective and first node prompt**
- Ask: "What is the overall objective of this pipeline?"
- Ask: "What should the first node do?"

**Step 6: Auto-generate prompts for remaining nodes**
- Read each team's CLAUDE.md
- Generate specific prompts based on objective, capabilities, and position
- Each prompt must reference input.md and instruct to write to output.md

**Step 7: Present all prompts for confirmation**
```
Pipeline: tech-spec-pipeline
Objective: {objective}

  Node 1 — research-team [auto]
  Prompt: {prompt text}

  Node 2 — design-team [gate]
  Prompt: {prompt text}
```

**Step 8: Generate pipeline YAML**
- Assemble nodes JSON and run:
  `python -m scripts.create_pipeline --name "<name>" --objective "<objective>" --nodes '<json>' --json`
