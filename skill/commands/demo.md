---
name: ot:demo
description: Guided tutorial — experience a full pipeline in 5 minutes
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# O-Team Guided Demo

## Language

**IMPORTANT**: Before starting, detect language: `PYTHONPATH=.claude/skills/ot python -m scripts.config detect --json`. All user-facing text below is in English as examples — you MUST translate everything to the detected language (e.g., Traditional Chinese if zh-TW).

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

## Overview

This is an interactive tutorial. Walk the user through the full O-Team workflow, explaining each step and its corresponding command.

---

## Phase 1: Teams

Show:
```
Step 1/4 — Team Registration

In O-Team, each pipeline node is powered by a "team" — a folder with
CLAUDE.md that defines the team's identity and capabilities.

Normally you'd create teams with A-Team, then register them:
  /ot:reg add <path>

For this demo, I'll create 3 lightweight teams for you.
```

### Actions:
1. Find the demo team templates in the skill directory: `.claude/skills/ot/templates/demo-teams/`
   - If the templates directory doesn't exist, look for it relative to SKILL.md location
2. Copy the 3 team folders to `.o-team/demo-teams/` in the project:
   - `.o-team/demo-teams/scout/`
   - `.o-team/demo-teams/analyst/`
   - `.o-team/demo-teams/advisor/`
3. Register each team:
   - `python -m scripts.registry add .o-team/demo-teams/scout --json`
   - `python -m scripts.registry add .o-team/demo-teams/analyst --json`
   - `python -m scripts.registry add .o-team/demo-teams/advisor --json`
4. For each, generate a brief summary and capabilities and update:
   - Scout: summary="Quick research and fact-finding on any topic", capabilities="research,analysis,trends"
   - Analyst: summary="Opportunity and risk assessment with impact scoring", capabilities="analysis,evaluation,scoring"
   - Advisor: summary="Strategic recommendations and executive briefs", capabilities="strategy,recommendation,synthesis"
5. Show result:
```
  Registered 3 demo teams:
    Scout    — Quick research and fact-finding
    Analyst  — Opportunity and risk assessment
    Advisor  — Strategic recommendations

  Tip: Use /ot:reg to manage your teams anytime.
```

AskUserQuestion: "Ready for the next step?" → "Continue" / "Show me /ot:reg first"

If "Show me /ot:reg first": run `python -m scripts.registry list --json`, display, then continue.

---

## Phase 2: Pipeline

Show:
```
Step 2/4 — Pipeline Creation

A pipeline chains teams into a workflow. Each team becomes a "node"
that processes input and passes results to the next team.

Normally you'd use /ot:build to interactively create a pipeline.

For this demo, I'll create a "Quick Insight" pipeline:

  Node 1 — Scout [auto]
  Researches the topic: key facts, trends, major players

  Node 2 — Analyst [auto]
  Finds top 3 opportunities and top 3 risks with impact ratings

  Node 3 — Advisor [gate]
  Produces a one-page executive brief with Go / Watch / Pass recommendation

  auto = runs and continues automatically
  gate = pauses for your review (you can approve, reject, or edit)

  Tip: Use /ot:build to create your own pipelines.
```

### Actions:
1. Create the pipeline:
```
python -m scripts.create_pipeline \
  --name "Quick Insight" \
  --objective "Research a topic and produce a strategic brief with actionable recommendation" \
  --nodes '[
    {"team": "scout", "mode": "auto", "prompt": "Research the provided topic thoroughly. Find 5 key facts, current trends, and major players. Structure your findings clearly with sources."},
    {"team": "analyst", "mode": "auto", "prompt": "Based on the research from the previous step, identify the top 3 opportunities and top 3 risks. Rate each on impact (High/Medium/Low) and provide brief justification."},
    {"team": "advisor", "mode": "gate", "prompt": "Synthesize the research and risk analysis from previous steps into a one-page executive brief. Include: 1) Situation summary (3 sentences), 2) Key opportunities and risks, 3) Clear recommendation: Go / Watch / Pass with reasoning, 4) Suggested next steps if Go."}
  ]' --json
```

2. Show: "Pipeline 'Quick Insight' created."

AskUserQuestion: "Ready to run it?" → "Continue" / "Show me /ot:pipe first"

If "Show me /ot:pipe first": show the pipeline details, then continue.

---

## Phase 3: Run

Show:
```
Step 3/4 — Pipeline Execution

Now let's run the pipeline! This is what /ot:run does.
I'll execute each node and show you the progress in real-time.
```

AskUserQuestion: "What topic would you like to analyze? (e.g., AI pet care app, EV charging market, remote work tools)"

### Actions:
1. Write user input to `.o-team/tmp-input.md`
2. Setup run: `python -m scripts.setup_run .o-team/pipelines/quick-insight.yaml --input-file .o-team/tmp-input.md --json`
3. Execute each node using the orchestrator pattern from `/ot:run` (Step 4):
   - For each node: announce → execute in background → monitor → handle result
   - Between nodes, explain what just happened
   - After Node 1 completes: "Scout finished researching. Results passed to Analyst automatically (auto mode)."
   - After Node 2 completes: "Analyst finished the assessment. Now Advisor will create the brief."
   - At Node 3 (gate): explain the gate concept before showing output:

```
This is a gate node. The pipeline pauses so you can review the output.

In a real workflow, you'd use this for quality control — reviewing
deliverables before they move forward or become the final output.

Your options:
  View full output — read the complete deliverable first
  Approve — accept the result
  Reject  — discard and re-run this node
  Edit    — view the full content, then tell me what to change
```

Then use AskUserQuestion with the standard gate options.

---

## Phase 4: Summary

After pipeline completes, show:

```
Step 4/4 — Done!

You just experienced the full O-Team workflow:
  1. Register teams    →  /ot:reg add <path>
  2. Build a pipeline  →  /ot:build
  3. Run it            →  /ot:run [<name>]
  4. Review at gates   →  (built into /ot:run)

Other useful commands:
  /ot:pipe             →  View/manage saved pipelines
  /ot:status           →  Check running pipeline status
  /ot:runs             →  View run history
  /ot:clean            →  Clean up old runs
  /ot:config           →  Settings (statusline, language)

Next steps:
  1. Create real teams with A-Team (github.com/chemistrywow31/A-Team)
  2. Register them: /ot:reg add <team-folder>
  3. Build your first custom pipeline: /ot:build
```

AskUserQuestion: "Show full output" / "Done"
