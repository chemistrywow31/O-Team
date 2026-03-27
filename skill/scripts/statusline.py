#!/usr/bin/env python3
"""O-Team statusline for claude-hud --extra-cmd.

Reads ~/.o-team/status.json and outputs { "label": "..." } JSON
for display in the claude-hud status bar.

Usage (as claude-hud --extra-cmd):
    --extra-cmd "python3 /path/to/statusline.py"

Output format:
    { "label": "O-Team [2/5] 01-research | Tool: Read" }

Returns nothing (empty output) when no pipeline is running.
"""

import json
import sys
import time
from pathlib import Path

STATUS_FILE = Path.home() / ".o-team" / "status.json"

# Consider status stale after 60 seconds (pipeline likely crashed)
STALE_THRESHOLD_SECONDS = 60


def main() -> None:
    if not STATUS_FILE.exists():
        return

    try:
        # Check if file is stale
        mtime = STATUS_FILE.stat().st_mtime
        if time.time() - mtime > STALE_THRESHOLD_SECONDS:
            # Status is stale — pipeline likely finished or crashed
            STATUS_FILE.unlink(missing_ok=True)
            return

        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    phase = data.get("phase", "")
    progress = data.get("progress", "")
    node = data.get("node", "")
    tool = data.get("tool", "")
    agent = data.get("agent", "")
    agent_desc = data.get("agent_desc", "")

    # Build detail part
    if phase == "tool" and tool:
        detail = tool
    elif phase == "agent" and agent:
        detail = f"Agent:{agent}" + (f" {agent_desc}" if agent_desc else "")
    elif phase == "complete":
        cost = data.get("cost", 0)
        dur = data.get("duration_ms", 0)
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

    # Keep label short — claude-hud truncates at 50 chars
    label = f"O [{progress}] {node} {detail}"
    if len(label) > 50:
        label = label[:49] + "…"

    print(json.dumps({"label": label}))


if __name__ == "__main__":
    main()
