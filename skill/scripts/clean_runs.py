"""O-Team CLI — Clean up run directories.

Usage:
    python -m scripts.clean_runs [run-id] [--all] [--state <filter>] [--project-dir <path>] [--json]

Without arguments: shows disk usage summary.
With run-id: removes that specific run.
With --all: removes all runs.
With --state: removes runs matching the state filter.
"""

import argparse
import shutil
import sys
from pathlib import Path

from . import utils


def _get_dir_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def clean_runs(
    run_id: str | None = None,
    clean_all: bool = False,
    state_filter: str | None = None,
    project_dir: Path | None = None,
) -> dict:
    """Clean up run directories."""
    proj_dir = utils.ensure_project_dir(project_dir)
    runs_dir = proj_dir / utils.RUNS_DIR_NAME

    archive_dir_path = proj_dir / utils.ARCHIVE_DIR_NAME
    if not runs_dir.exists() and not archive_dir_path.exists():
        return {"success": True, "removed": 0, "message": "No runs directory"}

    if run_id:
        # Remove specific run (search both runs/ and archive/)
        target = utils.find_run_dir(run_id, proj_dir)
        if not target:
            return {"success": False, "error": f"Run '{run_id}' not found"}
        size = _get_dir_size(target)
        shutil.rmtree(target)
        return {
            "success": True,
            "removed": 1,
            "freed": _human_size(size),
            "message": f"Removed run '{run_id}' ({_human_size(size)})",
        }

    # Collect targets (from both runs/ and archive/)
    all_dirs = list(runs_dir.iterdir()) if runs_dir.exists() else []
    archive_dir = proj_dir / utils.ARCHIVE_DIR_NAME
    if archive_dir.exists():
        all_dirs.extend(archive_dir.iterdir())

    targets = []
    for entry in sorted(all_dirs):
        if not entry.is_dir():
            continue
        meta_file = entry / "meta.json"
        state = "UNKNOWN"
        if meta_file.exists():
            try:
                meta = utils.read_json(meta_file)
                state = meta.get("state", "UNKNOWN")
            except Exception:
                pass

        if state_filter and state != state_filter.upper():
            continue

        if clean_all or state_filter:
            targets.append((entry, state))

    if not clean_all and not state_filter:
        # Just show summary (include both runs/ and archive/)
        total_size = 0
        run_count = 0
        archive_count = 0
        state_counts = {}
        if runs_dir.exists():
            for entry in runs_dir.iterdir():
                if not entry.is_dir():
                    continue
                run_count += 1
                total_size += _get_dir_size(entry)
                meta_file = entry / "meta.json"
                state = "UNKNOWN"
                if meta_file.exists():
                    try:
                        meta = utils.read_json(meta_file)
                        state = meta.get("state", "UNKNOWN")
                    except Exception:
                        pass
                state_counts[state] = state_counts.get(state, 0) + 1

        archive_dir = proj_dir / utils.ARCHIVE_DIR_NAME
        if archive_dir.exists():
            for entry in archive_dir.iterdir():
                if not entry.is_dir():
                    continue
                archive_count += 1
                total_size += _get_dir_size(entry)

        return {
            "success": True,
            "summary": True,
            "total_runs": run_count,
            "archived_runs": archive_count,
            "total_size": _human_size(total_size),
            "by_state": state_counts,
        }

    # Remove targets
    total_freed = 0
    for target_path, _ in targets:
        total_freed += _get_dir_size(target_path)
        shutil.rmtree(target_path)

    return {
        "success": True,
        "removed": len(targets),
        "freed": _human_size(total_freed),
        "message": f"Removed {len(targets)} runs ({_human_size(total_freed)})",
    }


def main():
    parser = argparse.ArgumentParser(description="Clean up run directories")
    parser.add_argument("run_id", nargs="?", default=None, help="Specific run ID to remove")
    parser.add_argument("--all", action="store_true", default=False, help="Remove all runs")
    parser.add_argument("--state", default=None, help="Remove runs matching state")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    proj_dir = Path(args.project_dir) if args.project_dir else None
    result = clean_runs(
        run_id=args.run_id,
        clean_all=args.all,
        state_filter=args.state,
        project_dir=proj_dir,
    )

    if args.json:
        utils.print_json(result)
    else:
        if result.get("summary"):
            archived = result.get("archived_runs", 0)
            archive_label = f"  Archived: {archived}" if archived else ""
            print(f"📊 Runs: {result['total_runs']}{archive_label}  Size: {result['total_size']}")
            for state, count in result["by_state"].items():
                print(f"   {state}: {count}")
        elif result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result.get('error')}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
