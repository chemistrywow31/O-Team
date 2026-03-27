"""O-Team CLI — Check run status.

Usage:
    python -m scripts.check_status <run-id> [--project-dir <path>] [--json]
    python -m scripts.check_status --live [--project-dir <path>] [--json]

With --live, reads the real-time status.json (no run-id needed).
"""

import argparse
import sys
from collections import deque
from pathlib import Path

from . import utils
from .stream_parser import STATUS_FILE_NAME


def check_status(run_id: str, project_dir: Path | None = None) -> dict:
    """Get the current status of a pipeline run."""
    proj_dir = utils.ensure_project_dir(project_dir)
    sandbox = proj_dir / utils.RUNS_DIR_NAME / run_id

    if not sandbox.exists():
        return {"success": False, "error": f"Run '{run_id}' not found"}

    meta_file = sandbox / "meta.json"
    if not meta_file.exists():
        return {"success": False, "error": f"Run '{run_id}' has no meta.json"}

    run_state = utils.read_json(meta_file)

    # Summarize node states
    node_summary = []
    for node in run_state["nodes"]:
        has_output = (sandbox / node["id"] / "output.md").exists()
        node_summary.append({
            "id": node["id"],
            "team": node["team"],
            "mode": node["mode"],
            "state": node["state"],
            "has_output": has_output,
            "exit_code": node.get("exit_code"),
            "error": node.get("error"),
        })

    result = {
        "success": True,
        "run_id": run_state["run_id"],
        "pipeline_name": run_state.get("pipeline_name", ""),
        "state": run_state["state"],
        "current_node_index": run_state.get("current_node_index", 0),
        "total_nodes": len(node_summary),
        "nodes": node_summary,
        "created_at": run_state.get("created_at"),
        "started_at": run_state.get("started_at"),
        "finished_at": run_state.get("finished_at"),
        "sandbox_path": str(sandbox),
    }

    # Merge live status if available
    live = _read_live_status(proj_dir)
    if live and live.get("run_id") == run_id:
        result["live"] = live

    # Read recent log lines from the currently running node
    current_idx = run_state.get("current_node_index", 0)
    if current_idx < len(run_state["nodes"]):
        current_node = run_state["nodes"][current_idx]
        log_file = sandbox / current_node["id"] / "run.log"
        if log_file.exists():
            result["recent_log"] = _tail(log_file, 10)

    return result


def check_live_status(project_dir: Path | None = None) -> dict:
    """Get the real-time stream status (no run-id needed).

    Reads status.json which is updated on every stream event.
    """
    proj_dir = utils.ensure_project_dir(project_dir)
    live = _read_live_status(proj_dir)

    if not live:
        return {"success": True, "running": False, "message": "No pipeline currently running"}

    return {
        "success": True,
        "running": True,
        **live,
    }


def _read_live_status(proj_dir: Path) -> dict | None:
    """Read the live status.json file (project-local or global)."""
    # Try project-local first
    local_path = proj_dir / STATUS_FILE_NAME
    if local_path.exists():
        try:
            return utils.read_json(local_path)
        except Exception:
            pass

    # Fall back to global
    global_path = Path.home() / ".o-team" / STATUS_FILE_NAME
    if global_path.exists():
        try:
            return utils.read_json(global_path)
        except Exception:
            pass

    return None


def _tail(filepath: Path, n: int = 10) -> list[str]:
    """Read the last n lines of a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return list(deque(f, maxlen=n))
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="Check run status")
    parser.add_argument("run_id", nargs="?", help="Run ID")
    parser.add_argument("--live", action="store_true",
                        help="Show real-time stream status (no run-id needed)")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    proj_dir = Path(args.project_dir) if args.project_dir else None

    if args.live:
        result = check_live_status(proj_dir)
    elif args.run_id:
        result = check_status(args.run_id, proj_dir)
    else:
        parser.error("Must provide a run_id or --live")
        return

    if args.json:
        utils.print_json(result)
    else:
        if args.live:
            _print_live(result)
        else:
            _print_human(result)

    sys.exit(0 if result["success"] else 1)


STATE_ICONS = {
    "PENDING": "⬜",
    "RUNNING": "🔄",
    "PAUSED_FOR_REVIEW": "⏸",
    "COMPLETE": "✅",
    "ERROR": "❌",
    "SKIPPED": "⏭",
    "CANCELLED": "🚫",
    "PAUSED": "⏸",
}


def _print_human(result: dict) -> None:
    if not result["success"]:
        print(f"❌ {result.get('error')}")
        return

    icon = STATE_ICONS.get(result["state"], "?")
    print(f"{icon} Run: {result['run_id']} — {result['pipeline_name']}")
    print(f"   State: {result['state']}")
    print(f"   Created: {result.get('created_at', '?')}")
    print()

    for node in result["nodes"]:
        n_icon = STATE_ICONS.get(node["state"], "?")
        mode_label = "auto" if node["mode"] == "auto" else "gate"
        output_label = "📄" if node["has_output"] else "  "
        line = f"   {n_icon} {node['id']} [{mode_label}] {output_label}"
        if node["error"]:
            line += f" — {node['error']}"
        print(line)

    # Live status
    live = result.get("live")
    if live:
        print()
        _print_live({"success": True, "running": True, **live})

    # Recent log
    log_lines = result.get("recent_log")
    if log_lines:
        print()
        print("   ── Recent activity ──")
        for line in log_lines:
            print(f"   │ {line.rstrip()}")


def _print_live(result: dict) -> None:
    if not result.get("running"):
        print("No pipeline currently running")
        return

    progress = result.get("progress", "?/?")
    node = result.get("node", "?")
    team = result.get("team", "?")
    phase = result.get("phase", "?")
    tool = result.get("tool", "")
    agent = result.get("agent", "")
    agent_desc = result.get("agent_desc", "")
    preview = result.get("preview", "")

    print(f"   [{progress}] {node} ({team})")

    if phase == "tool" and tool:
        print(f"   └─ Tool: {tool}")
    elif phase == "agent" and agent:
        desc = f" — {agent_desc}" if agent_desc else ""
        print(f"   └─ Agent: {agent}{desc}")
    elif phase == "running" and preview:
        print(f"   └─ {preview}")
    else:
        print(f"   └─ {phase}")


if __name__ == "__main__":
    main()
