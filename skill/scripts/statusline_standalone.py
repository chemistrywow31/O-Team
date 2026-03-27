#!/usr/bin/env python3
"""O-Team standalone statusline for Claude Code.

Reads Claude Code's stdin JSON and displays:
  - Pipeline status when a run is active
  - Basic session info (model, context) when idle

Usage in settings.json:
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.o-team/statusline_standalone.py"
  }

Claude Code pipes a JSON blob to stdin with session data including:
  model, cwd, session_id, context window info, etc.
"""

import json
import sys
import time
from pathlib import Path

STATUS_FILE = Path.home() / ".o-team" / "status.json"
STALE_THRESHOLD_SECONDS = 60


def read_stdin_json() -> dict:
    """Read and parse Claude Code's stdin JSON."""
    try:
        data = sys.stdin.read()
        if data:
            return json.loads(data)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def read_pipeline_status() -> dict | None:
    """Read active pipeline status. Returns None if no active run."""
    if not STATUS_FILE.exists():
        return None
    try:
        mtime = STATUS_FILE.stat().st_mtime
        if time.time() - mtime > STALE_THRESHOLD_SECONDS:
            STATUS_FILE.unlink(missing_ok=True)
            return None
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def format_context_bar(stdin_data: dict) -> str:
    """Format context usage as a compact bar."""
    # Claude Code provides various context fields
    # Try to extract context percentage
    context_pct = None

    # Check for context_window fields
    total = stdin_data.get("context_window_total", 0)
    used = stdin_data.get("context_window_used", 0)
    if total > 0 and used > 0:
        context_pct = int(used / total * 100)

    if context_pct is not None:
        # Simple bar: [####----] 45%
        filled = context_pct // 10
        bar = "#" * filled + "-" * (10 - filled)
        return f"[{bar}] {context_pct}%"
    return ""


def format_pipeline_status(status: dict) -> str:
    """Format pipeline status for display."""
    progress = status.get("progress", "")
    node = status.get("node", "")
    phase = status.get("phase", "")
    tool = status.get("tool", "")
    agent = status.get("agent", "")
    agent_desc = status.get("agent_desc", "")

    if phase == "tool" and tool:
        detail = tool
    elif phase == "agent" and agent:
        detail = f"Agent:{agent}"
        if agent_desc:
            detail += f" {agent_desc[:20]}"
    elif phase == "complete":
        cost = status.get("cost", 0)
        dur = status.get("duration_ms", 0)
        parts = []
        if dur:
            parts.append(f"{dur/1000:.0f}s")
        if cost:
            parts.append(f"${cost:.4f}")
        detail = f"Done({','.join(parts)})" if parts else "Done"
    elif phase == "error":
        detail = "ERR"
    else:
        detail = "..."

    return f"O-Team [{progress}] {node} | {detail}"


def main() -> None:
    stdin_data = read_stdin_json()
    pipeline = read_pipeline_status()

    parts = []

    # Model info
    model = stdin_data.get("model", "")
    if model:
        # Shorten model name
        short_model = model.replace("claude-", "").replace("-latest", "")
        parts.append(short_model)

    # Context bar
    ctx = format_context_bar(stdin_data)
    if ctx:
        parts.append(ctx)

    # Pipeline status (takes priority in display)
    if pipeline:
        parts.append(format_pipeline_status(pipeline))

    if parts:
        print(" | ".join(parts))
    else:
        print("O-Team")


if __name__ == "__main__":
    main()
