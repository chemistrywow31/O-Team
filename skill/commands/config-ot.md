---
name: ot:config
description: Interactive settings — statusline, language
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# Settings

## Script

```
PYTHONPATH=.claude/skills/o-team python -m scripts.<module> <args> --json
```

## Flow

1. Detect: `python -m scripts.config detect --json`
2. Show current config (statusline state, language)
3. AskUserQuestion: "Statusline setup" / "Language" / "Done"

**Statusline**: Based on detected state, offer merge/replace/keep options.
Apply: `python -m scripts.config apply <merge|o-team|keep|restore> --json`

**Language**: AskUserQuestion → English / 繁體中文
Apply: `python -m scripts.config set-language <en|zh-TW> --json`
