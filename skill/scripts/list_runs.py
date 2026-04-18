"""O-Team CLI — List pipeline run history.

Usage:
    python -m scripts.list_runs [--state <filter>] [--project-dir <path>] [--json]
"""

import argparse
import sys
from pathlib import Path

from . import utils


def list_runs(
    state_filter: str | None = None,
    project_dir: Path | None = None,
) -> dict:
    """List all pipeline runs in the project."""
    proj_dir = utils.ensure_project_dir(project_dir)
    runs_dir = proj_dir / utils.RUNS_DIR_NAME
    archive_dir = proj_dir / utils.ARCHIVE_DIR_NAME

    # Collect run directories from both runs/ and archive/
    run_dirs = []
    if runs_dir.exists():
        run_dirs.extend(runs_dir.iterdir())
    run_dirs.extend(utils.iter_archive_run_dirs(archive_dir))

    if not run_dirs:
        return {"success": True, "total": 0, "runs": []}

    runs = []
    for entry in sorted(run_dirs, key=lambda e: e.stat().st_mtime, reverse=True):
        if not entry.is_dir():
            continue
        meta_file = entry / "meta.json"
        if not meta_file.exists():
            continue

        try:
            meta = utils.read_json(meta_file)
        except Exception:
            continue

        state = meta.get("state", "UNKNOWN")
        if state_filter and state != state_filter.upper():
            continue

        # Count node states
        nodes = meta.get("nodes", [])
        completed = sum(1 for n in nodes if n.get("state") == "COMPLETE")

        runs.append({
            "run_id": meta.get("run_id", entry.name),
            "run_name": meta.get("run_name"),
            "pipeline_name": meta.get("pipeline_name", "?"),
            "state": state,
            "archived": meta.get("archived", False),
            "nodes_total": len(nodes),
            "nodes_completed": completed,
            "created_at": meta.get("created_at", "?"),
            "finished_at": meta.get("finished_at"),
        })

    return {
        "success": True,
        "total": len(runs),
        "runs": runs,
    }


def main():
    parser = argparse.ArgumentParser(description="List pipeline runs")
    parser.add_argument("--state", default=None,
                        help="Filter by state (PENDING, RUNNING, PAUSED, COMPLETE, ERROR, CANCELLED)")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    proj_dir = Path(args.project_dir) if args.project_dir else None
    result = list_runs(state_filter=args.state, project_dir=proj_dir)

    if args.json:
        utils.print_json(result)
    else:
        _print_human(result)


STATE_ICONS = {
    "PENDING": "⬜",
    "RUNNING": "🔄",
    "PAUSED": "⏸",
    "COMPLETE": "✅",
    "ERROR": "❌",
    "CANCELLED": "🚫",
}


def _print_human(result: dict) -> None:
    if result["total"] == 0:
        print("(無執行紀錄)")
        return

    print(f"執行紀錄 ({result['total']}):\n")
    for run in result["runs"]:
        icon = STATE_ICONS.get(run["state"], "?")
        progress = f"{run['nodes_completed']}/{run['nodes_total']}"
        label = run["run_id"]
        if run.get("run_name"):
            label = f"{run['run_name']}-{run['run_id']}"
        archive_tag = " 📦" if run.get("archived") else ""
        print(f"  {icon} {label} — {run['pipeline_name']}{archive_tag}")
        print(f"     State: {run['state']}  Progress: {progress}  Created: {run['created_at']}")
        if run["finished_at"]:
            print(f"     Finished: {run['finished_at']}")
        print()


if __name__ == "__main__":
    main()
