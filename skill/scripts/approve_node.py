"""O-Team CLI — Gate node operations (approve, reject, abort, skip).

Usage:
    python -m scripts.approve_node <run-id> <node-id> <action>
        [--project-dir <path>]
        [--json]

Actions:
    approve  — Accept output, transfer to next node, continue pipeline
    reject   — Discard output, re-execute this node
    skip     — Skip this node, proceed to next
    abort    — Cancel the entire pipeline run
"""

import argparse
import shutil
import sys
from pathlib import Path

from . import utils


VALID_ACTIONS = ("approve", "reject", "skip", "abort")


def approve_node(
    run_id: str,
    node_id: str,
    action: str,
    project_dir: Path | None = None,
) -> dict:
    """Perform a gate action on a paused or errored node.

    Returns dict with operation result.
    """
    if action not in VALID_ACTIONS:
        return {
            "success": False,
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(VALID_ACTIONS)}",
        }

    proj_dir = utils.ensure_project_dir(project_dir)
    sandbox = utils.find_run_dir(run_id, proj_dir)

    if not sandbox:
        return {
            "success": False,
            "error": f"Run '{run_id}' not found",
        }

    meta_file = sandbox / "meta.json"
    if not meta_file.exists():
        return {
            "success": False,
            "error": f"Run '{run_id}' has no meta.json",
        }

    run_state = utils.read_json(meta_file)

    # Find the node
    node = None
    node_index = None
    for i, n in enumerate(run_state["nodes"]):
        if n["id"] == node_id:
            node = n
            node_index = i
            break

    if node is None:
        return {
            "success": False,
            "error": f"Node '{node_id}' not found in run '{run_id}'",
        }

    # Validate node state
    valid_states = ("PAUSED_FOR_REVIEW", "ERROR")
    if node["state"] not in valid_states:
        return {
            "success": False,
            "error": f"Node '{node_id}' is in state '{node['state']}', must be one of: {', '.join(valid_states)}",
        }

    # Dispatch action
    if action == "approve":
        return _do_approve(run_state, node, node_index, sandbox)
    elif action == "reject":
        return _do_reject(run_state, node, node_index, sandbox)
    elif action == "skip":
        return _do_skip(run_state, node, node_index, sandbox)
    elif action == "abort":
        return _do_abort(run_state, sandbox)


def _do_approve(run_state: dict, node: dict, node_index: int, sandbox: Path) -> dict:
    """Approve: mark complete, transfer output, prepare for resume."""
    node["state"] = "COMPLETE"
    nodes = run_state["nodes"]

    # Transfer output to next node
    if node_index + 1 < len(nodes):
        next_node = nodes[node_index + 1]
        src = sandbox / node["id"] / "output.md"
        dst = sandbox / next_node["id"] / "input.md"
        if src.exists():
            shutil.copy2(src, dst)
        else:
            utils.write_text(dst, "")

    # Update run state for resume
    run_state["current_node_index"] = node_index + 1
    run_state["state"] = "PAUSED"  # Will be set to RUNNING on resume
    utils.write_json(sandbox / "meta.json", run_state)

    remaining = len(nodes) - node_index - 1
    if remaining == 0:
        # This was the last node
        run_state["state"] = "COMPLETE"
        run_state["finished_at"] = utils.now_iso()
        utils.write_json(sandbox / "meta.json", run_state)

        return {
            "success": True,
            "action": "approve",
            "run_id": run_state["run_id"],
            "node_id": node["id"],
            "state": "COMPLETE",
            "message": f"Pipeline complete. Final output: {sandbox / node['id'] / 'output.md'}",
        }

    return {
        "success": True,
        "action": "approve",
        "run_id": run_state["run_id"],
        "node_id": node["id"],
        "next_node": nodes[node_index + 1]["id"],
        "remaining": remaining,
        "message": f"Node approved. Resume with: python -m scripts.run_pipeline --resume {run_state['run_id']}",
    }


def _do_reject(run_state: dict, node: dict, node_index: int, sandbox: Path) -> dict:
    """Reject: reset node to PENDING, clear output, prepare for re-execution."""
    node["state"] = "PENDING"
    node["exit_code"] = None
    node["error"] = None
    node["started_at"] = None
    node["finished_at"] = None

    # Remove output.md (will be regenerated)
    output_file = sandbox / node["id"] / "output.md"
    if output_file.exists():
        output_file.unlink()

    # Remove run.log
    log_file = sandbox / node["id"] / "run.log"
    if log_file.exists():
        log_file.unlink()

    run_state["current_node_index"] = node_index
    run_state["state"] = "PAUSED"
    utils.write_json(sandbox / "meta.json", run_state)

    return {
        "success": True,
        "action": "reject",
        "run_id": run_state["run_id"],
        "node_id": node["id"],
        "message": f"Node rejected and reset. Re-run with: python -m scripts.run_pipeline --resume {run_state['run_id']}",
    }


def _do_skip(run_state: dict, node: dict, node_index: int, sandbox: Path) -> dict:
    """Skip: mark as SKIPPED, transfer whatever input exists to next node."""
    node["state"] = "SKIPPED"
    nodes = run_state["nodes"]

    # Transfer current input as-is to next node (skip this step's processing)
    if node_index + 1 < len(nodes):
        next_node = nodes[node_index + 1]
        # If output exists, use it; otherwise pass through input
        src = sandbox / node["id"] / "output.md"
        if not src.exists():
            src = sandbox / node["id"] / "input.md"
        dst = sandbox / next_node["id"] / "input.md"
        if src.exists():
            shutil.copy2(src, dst)

    run_state["current_node_index"] = node_index + 1
    run_state["state"] = "PAUSED"
    utils.write_json(sandbox / "meta.json", run_state)

    remaining = len(nodes) - node_index - 1
    if remaining == 0:
        run_state["state"] = "COMPLETE"
        run_state["finished_at"] = utils.now_iso()
        utils.write_json(sandbox / "meta.json", run_state)
        return {
            "success": True,
            "action": "skip",
            "run_id": run_state["run_id"],
            "node_id": node["id"],
            "state": "COMPLETE",
            "message": "Node skipped. Pipeline complete.",
        }

    return {
        "success": True,
        "action": "skip",
        "run_id": run_state["run_id"],
        "node_id": node["id"],
        "next_node": nodes[node_index + 1]["id"],
        "remaining": remaining,
        "message": f"Node skipped. Resume with: python -m scripts.run_pipeline --resume {run_state['run_id']}",
    }


def _do_abort(run_state: dict, sandbox: Path) -> dict:
    """Abort: cancel the entire pipeline run."""
    # Mark all pending nodes as SKIPPED
    for node in run_state["nodes"]:
        if node["state"] in ("PENDING", "PAUSED_FOR_REVIEW"):
            node["state"] = "SKIPPED"

    run_state["state"] = "CANCELLED"
    run_state["finished_at"] = utils.now_iso()
    utils.write_json(sandbox / "meta.json", run_state)

    return {
        "success": True,
        "action": "abort",
        "run_id": run_state["run_id"],
        "state": "CANCELLED",
        "message": "Pipeline run cancelled.",
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Gate node operations")
    parser.add_argument("run_id", help="Run ID")
    parser.add_argument("node_id", help="Node ID")
    parser.add_argument("action", choices=VALID_ACTIONS, help="Action to perform")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    proj_dir = Path(args.project_dir) if args.project_dir else None

    result = approve_node(
        run_id=args.run_id,
        node_id=args.node_id,
        action=args.action,
        project_dir=proj_dir,
    )

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result.get('error', 'Unknown error')}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
