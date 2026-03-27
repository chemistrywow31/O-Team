"""O-Team CLI — Mark a node complete and transfer output.

Usage:
    python -m scripts.complete_node <sandbox-path> <node-id> [--skip] [--json]

Marks node COMPLETE (or SKIPPED with --skip), transfers output.md
to the next node's input.md, and checks if the pipeline is done.
"""

import argparse
import shutil
import sys
from pathlib import Path

from . import utils


def complete_node(
    sandbox_path: str,
    node_id: str,
    skip: bool = False,
) -> dict:
    """Mark a node complete and transfer output to next node.

    Returns:
        dict with success, pipeline state, and next node info.
    """
    sandbox = Path(sandbox_path)
    meta_file = sandbox / "meta.json"

    if not meta_file.exists():
        return {"success": False, "error": f"No meta.json at {sandbox}"}

    meta = utils.read_json(meta_file)

    # Find node
    node = None
    node_index = -1
    for i, n in enumerate(meta["nodes"]):
        if n["id"] == node_id:
            node = n
            node_index = i
            break

    if node is None:
        return {"success": False, "error": f"Node '{node_id}' not found"}

    # Update state
    node["state"] = "SKIPPED" if skip else "COMPLETE"

    # Transfer output to next node
    next_node_info = None
    if node_index + 1 < len(meta["nodes"]):
        next_node = meta["nodes"][node_index + 1]
        src = sandbox / node["id"] / "output.md"
        dst = sandbox / next_node["id"] / "input.md"

        if not skip and src.exists():
            shutil.copy2(src, dst)
        else:
            utils.write_text(dst, "")

        next_node_info = {
            "id": next_node["id"],
            "team": next_node["team"],
            "mode": next_node["mode"],
            "index": node_index + 1,
        }

    # Check if all nodes are done
    all_done = all(
        n["state"] in ("COMPLETE", "SKIPPED") for n in meta["nodes"]
    )
    if all_done:
        meta["state"] = "COMPLETE"
        meta["finished_at"] = utils.now_iso()
    else:
        meta["state"] = "RUNNING"

    utils.write_json(meta_file, meta)

    result = {
        "success": True,
        "node_id": node_id,
        "node_state": node["state"],
        "pipeline_state": meta["state"],
        "run_id": meta["run_id"],
    }

    if next_node_info:
        result["next_node"] = next_node_info
    if all_done:
        last_node = meta["nodes"][-1]
        result["output_path"] = str(sandbox / last_node["id"] / "output.md")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Complete a node and transfer output")
    parser.add_argument("sandbox", help="Sandbox directory path")
    parser.add_argument("node_id", help="Node ID to complete")
    parser.add_argument("--skip", action="store_true", default=False,
                        help="Mark as SKIPPED instead of COMPLETE")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    result = complete_node(args.sandbox, args.node_id, skip=args.skip)

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            action = "skipped" if args.skip else "completed"
            print(f"✅ Node '{args.node_id}' {action}")
            if result.get("next_node"):
                nxt = result["next_node"]
                print(f"   → Next: {nxt['id']} ({nxt['team']})")
            if result["pipeline_state"] == "COMPLETE":
                print(f"   🏁 Pipeline complete")
                print(f"   Output: {result.get('output_path')}")
        else:
            print(f"❌ {result.get('error')}")

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
