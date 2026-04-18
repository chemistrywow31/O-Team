"""O-Team CLI — Finalize a completed pipeline run.

Combines completion summary + archive into a single atomic operation
so the orchestrating Claude does not need to remember multiple steps.

Usage:
    # Interactive (prompts for archive name):
    python -m scripts.finalize_run <sandbox_path> --json

    # Non-interactive (provide name directly):
    python -m scripts.finalize_run <sandbox_path> --name "my-run" --json

    # Skip archiving:
    python -m scripts.finalize_run <sandbox_path> --skip-archive --json
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from . import utils


def finalize_run(
    sandbox_path_str: str,
    name: str | None = None,
    skip_archive: bool = False,
) -> dict:
    """Finalize a completed pipeline run.

    1. Reads run state and identifies final output
    2. Archives if name provided (or prompts interactively)
    3. Returns structured result with output path and archive info

    Args:
        sandbox_path_str: Path to the run sandbox
        name: Archive name (None = interactive prompt, "" = skip)
        skip_archive: Skip archive step entirely

    Returns:
        dict with finalization result
    """
    sandbox = utils.resolve_path(sandbox_path_str)

    if not sandbox.exists():
        return {"success": False, "error": f"Sandbox not found: {sandbox}"}

    meta_path = sandbox / "meta.json"
    if not meta_path.exists():
        return {"success": False, "error": f"No meta.json in sandbox: {sandbox}"}

    run_state = utils.read_json(meta_path)
    run_id = run_state.get("run_id", "unknown")
    pipeline_name = run_state.get("pipeline_name", "unknown")

    # Find final output
    nodes = run_state.get("nodes", [])
    last_node = nodes[-1] if nodes else None
    output_path = ""
    if last_node:
        out = sandbox / last_node["id"] / "output.md"
        if out.exists():
            output_path = str(out)

    result = {
        "success": True,
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "output_path": output_path,
        "archived": False,
        "archive_path": "",
    }

    if skip_archive:
        return result

    # Determine archive name
    archive_name = name
    if archive_name is None and sys.stdin.isatty():
        # Interactive: prompt user
        try:
            archive_name = input(
                f"\n📦 Name this run for archiving? (Enter to skip): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            archive_name = ""

    if not archive_name:
        return result

    # Sanitize name
    sanitized = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', archive_name)
    if not sanitized:
        return result

    # Perform archive — partition by local date: archive/YYYY/MM/DD/<name>-<uuid>
    project_dir = sandbox.parent.parent  # .o-team/runs/<id> → .o-team
    archive_dir = project_dir / utils.ARCHIVE_DIR_NAME
    date_partition = datetime.now().strftime("%Y/%m/%d")
    target_dir = archive_dir / date_partition
    target_dir.mkdir(parents=True, exist_ok=True)

    new_folder = f"{sanitized}-{run_id}"
    new_path = target_dir / new_folder

    if new_path.exists():
        # Avoid collision
        new_folder = f"{sanitized}-{run_id}-2"
        new_path = target_dir / new_folder

    try:
        sandbox.rename(new_path)
    except OSError as e:
        result["archive_error"] = str(e)
        return result

    # Update meta.json in new location
    run_state["run_name"] = sanitized
    run_state["archived"] = True
    utils.write_json(new_path / "meta.json", run_state)

    # Update output path to new location
    if last_node:
        new_out = new_path / last_node["id"] / "output.md"
        if new_out.exists():
            output_path = str(new_out)

    result["archived"] = True
    result["archive_path"] = str(new_path)
    result["archive_name"] = sanitized
    result["output_path"] = output_path

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Finalize a completed pipeline run")
    parser.add_argument("sandbox", help="Path to run sandbox")
    parser.add_argument("--name", default=None, help="Archive name (skip prompt)")
    parser.add_argument(
        "--skip-archive", action="store_true", default=False,
        help="Skip archive step",
    )
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    result = finalize_run(args.sandbox, args.name, args.skip_archive)

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"✅ Run {result['run_id']} finalized")
            if result["output_path"]:
                print(f"   Output: {result['output_path']}")
            if result["archived"]:
                print(f"   Archived: {result['archive_path']}")
        else:
            print(f"❌ {result.get('error')}")

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
