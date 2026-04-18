"""O-Team CLI — Archive a run with a human-readable name.

Usage:
    python -m scripts.archive_run <sandbox-path> --name <run-name> [--json]

Renames the run folder to <name>-<run_id> and moves it to archive/.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from . import utils


def archive_run(sandbox_path: str, run_name: str) -> dict:
    """Archive a run by naming it and moving to archive/.

    Args:
        sandbox_path: Path to the run's sandbox directory.
        run_name: Human-readable name for the run.

    Returns:
        dict with success status and new path.
    """
    sandbox = Path(sandbox_path)
    meta_file = sandbox / "meta.json"

    if not meta_file.exists():
        return {"success": False, "error": f"No meta.json at {sandbox}"}

    meta = utils.read_json(meta_file)

    if meta.get("archived"):
        return {"success": False, "error": f"Run '{meta['run_id']}' is already archived"}

    # Sanitize: keep alphanumeric, dash, underscore, CJK characters
    sanitized = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', run_name)
    if not sanitized:
        return {"success": False, "error": "Run name is empty after sanitization"}

    run_id = meta["run_id"]
    new_folder_name = f"{sanitized}-{run_id}"

    # Resolve project dir (sandbox is at .o-team/runs/<id>)
    project_dir = sandbox.parent.parent
    archive_dir = project_dir / utils.ARCHIVE_DIR_NAME
    date_partition = datetime.now().strftime("%Y/%m/%d")
    target_dir = archive_dir / date_partition
    target_dir.mkdir(parents=True, exist_ok=True)

    new_path = target_dir / new_folder_name

    if new_path.exists():
        return {"success": False, "error": f"Archive path already exists: {new_path}"}

    sandbox.rename(new_path)

    # Update meta.json
    meta["run_name"] = sanitized
    meta["archived"] = True
    utils.write_json(new_path / "meta.json", meta)

    return {
        "success": True,
        "run_id": run_id,
        "run_name": sanitized,
        "archive_path": str(new_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Archive a run with a name")
    parser.add_argument("sandbox", help="Sandbox directory path")
    parser.add_argument("--name", required=True, help="Human-readable name for the run")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    result = archive_run(args.sandbox, args.name)

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"📁 Archived: {result['run_name']}-{result['run_id']}")
            print(f"   Path: {result['archive_path']}")
        else:
            print(f"❌ {result.get('error')}")

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
