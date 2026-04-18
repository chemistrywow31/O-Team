"""O-Team CLI — Setup a new pipeline run (sandbox only, no execution).

Usage:
    python -m scripts.setup_run <pipeline-yaml> [--input-file <path>] [--json]
    python -m scripts.setup_run <pipeline-yaml> --from <node-num> [--clone <run-id>] [--input-file <path>] [--json]

Creates UUID sandbox, copies team configs, writes initial input.
With --from, clones a previous run and starts from a specific node.
Returns run state for orchestration by the caller.
"""

import argparse
import shutil
import sys
from pathlib import Path

from . import utils
from .validate_pipeline import validate_pipeline


def setup_run(
    pipeline_path: str,
    input_content: str | None = None,
    project_dir: Path | None = None,
    from_node: int | None = None,
    clone_run_id: str | None = None,
) -> dict:
    """Create sandbox and prepare for execution, but do NOT execute.

    Args:
        pipeline_path: Path to pipeline YAML
        input_content: Initial input text (for node 0 or --from node)
        project_dir: Project directory
        from_node: 1-based node number to start from (skips earlier nodes)
        clone_run_id: Run ID to clone outputs from (auto-detects if omitted)

    Returns:
        dict with run_id, sandbox_path, node list, and start_from_index.
    """
    proj_dir = utils.ensure_project_dir(project_dir)

    # Validate
    validation = validate_pipeline(pipeline_path)
    if not validation["valid"]:
        return {
            "success": False,
            "error": "Pipeline validation failed",
            "validation": validation,
        }

    pipeline = validation["pipeline"]
    pipeline_slug = pipeline.get("slug", "")

    # Handle --from: find source run to clone from
    source_sandbox = None
    if from_node is not None:
        start_index = from_node - 1  # Convert to 0-based
        if start_index < 0 or start_index >= len(pipeline["nodes"]):
            return {
                "success": False,
                "error": f"Invalid --from value: {from_node}. Pipeline has {len(pipeline['nodes'])} nodes.",
            }
        if start_index == 0 and not input_content:
            return {
                "success": False,
                "error": "--from 1 is the same as a fresh run. Provide --input-file for initial input.",
            }

        source_sandbox = _find_source_run(
            clone_run_id, pipeline_slug, proj_dir, start_index
        )
        if source_sandbox is None:
            return {
                "success": False,
                "error": f"No previous run found to clone from."
                + (f" Run ID '{clone_run_id}' not found." if clone_run_id else ""),
            }
    else:
        start_index = 0

    # Create sandbox
    run_id = utils.generate_run_id()
    runs_dir = proj_dir / utils.RUNS_DIR_NAME
    sandbox = runs_dir / run_id

    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / "workspace").mkdir(exist_ok=True)

    # Create office folders and copy team configs
    pipeline_path = Path(pipeline_path) if isinstance(pipeline_path, str) else None
    nodes_state = []
    for i, node in enumerate(pipeline["nodes"]):
        office = sandbox / node["id"]
        office.mkdir(exist_ok=True)

        # Determine node type and setup accordingly
        has_team = bool(node.get("team")) and bool(node.get("team_path"))
        if has_team:
            team_path = Path(node["team_path"])
            utils.copy_team_config(team_path, office)
        else:
            # Prompt-only node: setup minimal office
            utils.setup_prompt_node(node, office, pipeline_path or Path.cwd())

        # Mark earlier nodes as COMPLETE when using --from
        if from_node is not None and i < start_index:
            state = "COMPLETE"
            # Copy output.md from source run
            if source_sandbox:
                src_output = source_sandbox / node["id"] / "output.md"
                if src_output.exists():
                    shutil.copy2(src_output, office / "output.md")
        else:
            state = "PENDING"

        nodes_state.append({
            "id": node["id"],
            "team": node.get("team", ""),
            "team_path": node.get("team_path", ""),
            "mode": node["mode"],
            "prompt": node.get("prompt", ""),
            "prompt_file": node.get("prompt_file", ""),
            "model": node.get("model", ""),
            "effort": node.get("effort", ""),
            "timeout": node.get("timeout", utils.DEFAULT_TIMEOUT),
            "node_type": "team" if has_team else "prompt",
            "state": state,
            "exit_code": None,
            "error": None,
            "started_at": None,
            "finished_at": None,
        })

    # Transfer input to the starting node
    if from_node is not None and start_index > 0:
        target_node_id = nodes_state[start_index]["id"]
        target_input = sandbox / target_node_id / "input.md"

        if input_content:
            # User provided custom input for the starting node
            utils.write_text(target_input, input_content)
        else:
            # Default: use previous node's output.md from source run
            prev_node_id = nodes_state[start_index - 1]["id"]
            src_output = source_sandbox / prev_node_id / "output.md"
            if src_output.exists():
                shutil.copy2(src_output, target_input)
            else:
                utils.write_text(target_input, "")
    elif input_content:
        # Fresh run: write input to first node
        first_node_id = nodes_state[0]["id"]
        input_path = sandbox / first_node_id / "input.md"
        utils.write_text(input_path, input_content)

    # Copy workspace from source run if cloning
    if source_sandbox:
        src_workspace = source_sandbox / "workspace"
        dst_workspace = sandbox / "workspace"
        if src_workspace.is_dir():
            for item in src_workspace.iterdir():
                if item.is_file():
                    shutil.copy2(item, dst_workspace / item.name)
                elif item.is_dir():
                    shutil.copytree(item, dst_workspace / item.name)

    # Save pipeline snapshot
    utils.write_yaml(sandbox / "snapshot.yaml", pipeline)

    # Build run state
    run_state = {
        "run_id": run_id,
        "pipeline_name": pipeline.get("name", ""),
        "pipeline_slug": pipeline_slug,
        "state": "PENDING",
        "nodes": nodes_state,
        "current_node_index": start_index,
        "sandbox_path": str(sandbox),
        "created_at": utils.now_iso(),
        "started_at": None,
        "finished_at": None,
    }
    if clone_run_id or source_sandbox:
        run_state["cloned_from"] = clone_run_id or source_sandbox.name

    utils.write_json(sandbox / "meta.json", run_state)

    result = {
        "success": True,
        "run_id": run_id,
        "sandbox_path": str(sandbox),
        "pipeline_name": pipeline.get("name", ""),
        "total_nodes": len(nodes_state),
        "start_from_index": start_index,
        "nodes": [
            {"id": n["id"], "team": n["team"], "mode": n["mode"], "state": n["state"]}
            for n in nodes_state
        ],
    }
    if source_sandbox:
        result["cloned_from"] = source_sandbox.name

    return result


def _find_source_run(
    run_id: str | None, pipeline_slug: str, proj_dir: Path, start_index: int
) -> Path | None:
    """Find a source run to clone from.

    If run_id is given, use that. Otherwise find the latest run
    for the same pipeline that has the required node outputs.
    """
    runs_dir = proj_dir / utils.RUNS_DIR_NAME
    if not runs_dir.exists() and not (proj_dir / utils.ARCHIVE_DIR_NAME).exists():
        return None

    if run_id:
        candidate = utils.find_run_dir(run_id, proj_dir)
        if candidate and (candidate / "meta.json").exists():
            return candidate
        return None

    # Find latest run for this pipeline with completed nodes before start_index
    all_dirs = list(runs_dir.iterdir()) if runs_dir.exists() else []
    archive_dir = proj_dir / utils.ARCHIVE_DIR_NAME
    if archive_dir.exists():
        all_dirs.extend(archive_dir.iterdir())

    best = None
    best_time = ""
    for entry in all_dirs:
        if not entry.is_dir():
            continue
        meta_file = entry / "meta.json"
        if not meta_file.exists():
            continue
        try:
            meta = utils.read_json(meta_file)
        except Exception:
            continue
        if meta.get("pipeline_slug") != pipeline_slug:
            continue
        # Check that nodes before start_index have output
        nodes = meta.get("nodes", [])
        if len(nodes) < start_index:
            continue
        has_outputs = all(
            (entry / nodes[i]["id"] / "output.md").exists()
            for i in range(start_index)
        )
        if not has_outputs:
            continue
        created = meta.get("created_at", "")
        if created > best_time:
            best_time = created
            best = entry

    return best


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Setup a new pipeline run")
    parser.add_argument("pipeline", help="Path to pipeline YAML")
    parser.add_argument("--input", default=None,
                        help="Initial input (text or file path)")
    parser.add_argument("--input-file", default=None,
                        help="Read initial input from this file")
    parser.add_argument("--from", dest="from_node", type=int, default=None,
                        help="Start from this node number (1-based). Clones prior outputs from latest run.")
    parser.add_argument("--clone", default=None,
                        help="Run ID to clone outputs from (used with --from)")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    proj_dir = Path(args.project_dir) if args.project_dir else None

    input_content = args.input
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            utils.print_json({"success": False, "error": f"Input file not found: {args.input_file}"})
            sys.exit(1)
        input_content = input_path.read_text(encoding="utf-8")

    result = setup_run(
        args.pipeline,
        input_content,
        proj_dir,
        from_node=args.from_node,
        clone_run_id=args.clone,
    )

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"✅ Run created: {result['run_id']}")
            print(f"   Sandbox: {result['sandbox_path']}")
            if result.get("cloned_from"):
                print(f"   Cloned from: {result['cloned_from']}")
            if result["start_from_index"] > 0:
                print(f"   Starting from node {result['start_from_index'] + 1}")
            for n in result["nodes"]:
                mode_icon = "⚡" if n["mode"] == "auto" else "⏸"
                state_icon = "✅" if n["state"] == "COMPLETE" else "⬜"
                print(f"   {state_icon} {mode_icon} {n['id']} ({n['team']})")
        else:
            print(f"❌ {result.get('error')}")

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
