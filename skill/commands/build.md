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

Find the o-team skill directory (contains `SKILL.md`): `.claude/skills/o-team/`.

**IMPORTANT**: Run scripts from the **project root** (not the skill directory), using `PYTHONPATH`:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module_name> <args> --json
```

## Flow

**Use AskUserQuestion for EVERY user interaction step.** Do NOT use free-form text conversation. Each step should present clear selectable options.

**Step 1: List registered teams**
- Run `PYTHONPATH=.claude/skills/o-team python -m scripts.registry list --json`
- Present numbered list with summaries and capabilities
- If no teams registered, tell user to register first and stop

**Step 2: Select teams**
- Use AskUserQuestion:
  - Question: "Select teams for this pipeline (enter numbers in execution order, comma-separated, e.g. 1,3,2)"
  - Show the numbered team list as context before the question

**Step 3: Set execution mode**
- Show default modes as a table: auto for all nodes except last (gate)
- Use AskUserQuestion:
  - Question: "Execution modes:"
  - Options:
    - "Use defaults (auto → ... → gate)"
    - "Customize modes"
- If "Customize": for each node, use AskUserQuestion with options "auto" / "gate"

**Step 4: Name the pipeline**
- Use AskUserQuestion:
  - Question: "Pipeline name:"

**Step 5: Objective and first node prompt**
- Use AskUserQuestion:
  - Question: "What is the overall objective of this pipeline?"
- Use AskUserQuestion:
  - Question: "What should the first node do? (starting prompt)"

**Step 6: Auto-generate prompts**
- Read each team's CLAUDE.md from their team_path
- Generate specific prompts for all subsequent nodes based on:
  - Pipeline objective
  - First node prompt
  - Each team's capabilities
  - Position in the pipeline and handoff relationship
- Prompt guidelines:
  - Do NOT reference input.md or output.md — the system automatically injects input context into the prompt and appends output instructions
  - For Node 1: reference the input contextually (e.g., "根據提供的研究主題" / "Based on the provided topic") since user's initial input is injected as "## Initial Input"
  - For subsequent nodes: reference the previous step's output contextually (e.g., "根據前一階段的調查報告" / "Based on the research report from the previous step") since it is injected as "## Context (from previous step)"
  - Focus prompts on WHAT to do and HOW to structure the deliverable

**Step 7: Review prompts**
- Present complete pipeline with all prompts:
```
Pipeline: {name}
Objective: {objective}

  Node 1 — {team} [auto]
  Prompt: {prompt text}

  Node 2 — {team} [gate]
  Prompt: {prompt text}
```
- Use AskUserQuestion:
  - Question: "Confirm pipeline?"
  - Options:
    - "Confirm and save"
    - "Modify a node (specify node number)"
    - "Cancel"
- If "Modify": ask which node, let user edit that prompt, then re-present

**Step 8: Generate pipeline YAML**
- Assemble nodes JSON and run:
  `PYTHONPATH=.claude/skills/o-team python -m scripts.create_pipeline --name "<name>" --objective "<objective>" --nodes '<json>' --json`
- Show result with file path
