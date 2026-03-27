"""O-Team CLI — Setup a new pipeline run (sandbox only, no execution).

Usage:
    python -m scripts.setup_run <pipeline-yaml> [--input <text-or-file>] [--json]

Creates UUID sandbox, copies team configs, writes initial input.
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
) -> dict:
    """Create sandbox and prepare for execution, but do NOT execute.

    Returns:
        dict with run_id, sandbox_path, and node list.
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

    # Create sandbox
    run_id = utils.generate_run_id()
    runs_dir = proj_dir / utils.RUNS_DIR_NAME
    sandbox = runs_dir / run_id

    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / "workspace").mkdir(exist_ok=True)

    # Create office folders and copy team configs
    nodes_state = []
    for node in pipeline["nodes"]:
        office = sandbox / node["id"]
        office.mkdir(exist_ok=True)

        team_path = Path(node["team_path"])
        _copy_team_config(team_path, office)

        nodes_state.append({
            "id": node["id"],
            "team": node["team"],
            "team_path": node["team_path"],
            "mode": node["mode"],
            "prompt": node["prompt"],
            "timeout": node.get("timeout", utils.DEFAULT_TIMEOUT),
            "state": "PENDING",
            "exit_code": None,
            "error": None,
            "started_at": None,
            "finished_at": None,
        })

    # Save pipeline snapshot
    utils.write_yaml(sandbox / "snapshot.yaml", pipeline)

    # Build run state
    run_state = {
        "run_id": run_id,
        "pipeline_name": pipeline.get("name", ""),
        "pipeline_slug": pipeline.get("slug", ""),
        "state": "PENDING",
        "nodes": nodes_state,
        "current_node_index": 0,
        "sandbox_path": str(sandbox),
        "created_at": utils.now_iso(),
        "started_at": None,
        "finished_at": None,
    }

    utils.write_json(sandbox / "meta.json", run_state)

    # Write initial input
    if input_content:
        first_node_id = nodes_state[0]["id"]
        input_path = sandbox / first_node_id / "input.md"
        potential_file = Path(input_content)
        if potential_file.exists() and potential_file.is_file():
            shutil.copy2(potential_file, input_path)
        else:
            utils.write_text(input_path, input_content)

    return {
        "success": True,
        "run_id": run_id,
        "sandbox_path": str(sandbox),
        "pipeline_name": pipeline.get("name", ""),
        "total_nodes": len(nodes_state),
        "nodes": [
            {"id": n["id"], "team": n["team"], "mode": n["mode"]}
            for n in nodes_state
        ],
    }


def _copy_team_config(team_path: Path, office: Path) -> None:
    """Copy CLAUDE.md and .claude/ directory into the office folder."""
    src_claude_md = team_path / "CLAUDE.md"
    if src_claude_md.exists():
        shutil.copy2(src_claude_md, office / "CLAUDE.md")

    src_claude_dir = team_path / ".claude"
    dst_claude_dir = office / ".claude"
    if src_claude_dir.is_dir():
        if dst_claude_dir.exists():
            shutil.rmtree(dst_claude_dir)
        shutil.copytree(src_claude_dir, dst_claude_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Setup a new pipeline run")
    parser.add_argument("pipeline", help="Path to pipeline YAML")
    parser.add_argument("--input", default=None,
                        help="Initial input (text or file path)")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    proj_dir = Path(args.project_dir) if args.project_dir else None
    result = setup_run(args.pipeline, args.input, proj_dir)

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"✅ Run created: {result['run_id']}")
            print(f"   Sandbox: {result['sandbox_path']}")
            for n in result["nodes"]:
                mode_icon = "⚡" if n["mode"] == "auto" else "⏸"
                print(f"   {mode_icon} {n['id']} ({n['team']})")
        else:
            print(f"❌ {result.get('error')}")

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
