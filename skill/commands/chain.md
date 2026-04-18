---
name: ot:chain
description: Build and run a prompt chain — from a file, directory, or interactively
argument-hint: "[<file.md> | <directory>]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Chain — Prompt Chain Runner

## Language

Detect language: `PYTHONPATH=.claude/skills/ot python -m scripts.config detect --json`. All user-facing text MUST be in the detected language.

## Script

```
PYTHONPATH=.claude/skills/ot python -m scripts.<module> <args> --json
```

## Flow

**Use AskUserQuestion for EVERY user interaction step.**

### Step 1: Determine mode

- **No argument** → Interactive mode (Step 2A)
- **Argument provided** → Detect mode (Step 2B)

### Step 2A: Interactive mode

Collect prompts step by step.

1. AskUserQuestion: "Step 1 — describe what this step does:"
2. AskUserQuestion: "Step 2 — next step (or 'done' to finish):"
3. Repeat until user says "done"
4. AskUserQuestion: "Name this chain? (Enter to skip)"

Build:
```bash
PYTHONPATH=.claude/skills/ot python -m scripts.chain --prompts '<json-array>' --name "<name>" --json
```

→ Go to Step 3.

### Step 2B: Detect and confirm

**First, detect what was found** — do NOT build yet:

```bash
PYTHONPATH=.claude/skills/ot python -m scripts.chain "<path>" --detect --json
```

**Present the detection result to the user:**

For single-file format:
```
Detected: single .md file (3 steps)

  1. Research — 你是研究員。蒐集技術現況...
  2. Analyze — 你是分析師。根據前一階段...
  3. Report — 你是顧問。根據分析結果...

Mode: all auto, last gate
```

For directory format:
```
Detected: directory (3 files)

  1. Research — 01-research.md
  2. Analyze — 02.md
  3. Report — 03-report.md

Mode: all auto, last gate
```

**AskUserQuestion: "Confirm and build? (Y / edit / cancel)"**

- **Y** → Build pipeline (Step 2C)
- **edit** → AskUserQuestion which step to change, apply edits, re-detect
- **cancel** → Stop

### Step 2C: Build pipeline

```bash
PYTHONPATH=.claude/skills/ot python -m scripts.chain "<path>" --json
```

→ Go to Step 3.

### Step 3: Summary

Show: pipeline name, step count, output YAML path.

### Step 4: Run

AskUserQuestion: "Run now? (Y/n)"

- **Yes**:
  1. Validate: `python -m scripts.validate_pipeline <pipeline-path> --json`
  2. AskUserQuestion: "Input for the first step:"
  3. Follow `/ot:run` Steps 3-5 (setup → execute loop → finalize)
- **No**: Done.
