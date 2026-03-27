---
name: o-team:config
description: Interactive settings — statusline, language
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# O-Team Config

First-time in this session? Show: **O-Team | Agent Office**

## Script Location

Find the o-team skill directory (contains `SKILL.md`): `.claude/skills/o-team/`.

**IMPORTANT**: Run scripts from the **project root** (not the skill directory), using `PYTHONPATH`:

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module_name> <args> --json
```

## Flow

**Step 1: Detect current state**
- Run `python -m scripts.config detect --json`

**Step 2: Show current config**
```
O-Team Settings

Statusline: {state}
Language: {detected language}
```

**Step 3: Ask what to configure** (AskUserQuestion)
- "Statusline setup"
- "Language"
- "Done"

**Step 4a: Statusline (if selected)**

Based on detected state, offer options via AskUserQuestion:

- `claude-hud` → Merge (recommended) / Replace / Keep
- `o-team-merged` → Already configured / Replace / Remove merge
- `o-team` → Already standalone / Restore previous
- `other` → Replace / Keep
- `none` → Enable (recommended) / Skip

Apply: `python -m scripts.config apply <merge|o-team|keep|restore> --json`

**Step 4b: Language (if selected)**

AskUserQuestion:
- "English"
- "繁體中文 (Traditional Chinese)"

Apply: `python -m scripts.config set-language <en|zh-TW> --json`

**Step 5: Confirm**
Show result. If statusline changed, mention restart needed.
