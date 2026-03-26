"""O-Team CLI — Check run status.

Usage:
    python -m scripts.check_status <run-id> [--project-dir <path>] [--json]
"""

import argparse
import sys
from pathlib import Path

from . import utils


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

    return {
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


def main():
    parser = argparse.ArgumentParser(description="Check run status")
    parser.add_argument("run_id", help="Run ID")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    proj_dir = Path(args.project_dir) if args.project_dir else None
    result = check_status(args.run_id, proj_dir)

    if args.json:
        utils.print_json(result)
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


if __name__ == "__main__":
    main()
