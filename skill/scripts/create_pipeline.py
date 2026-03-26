"""O-Team CLI — Pipeline YAML generator.

Usage:
    python -m scripts.create_pipeline \
        --name <pipeline-name> \
        --nodes <json-array> \
        [--objective <text>] \
        [--output <path>] \
        [--json]

Generates a pipeline YAML file from a JSON node configuration.
Validates all team references against the registry.
"""

import argparse
import json
import sys
from pathlib import Path

from . import utils


def create_pipeline(
    name: str,
    nodes_json: str,
    objective: str = "",
    output_path: str | None = None,
) -> dict:
    """Create a pipeline YAML from node configuration.

    Args:
        name: Pipeline name (will be slugified for filename)
        nodes_json: JSON string of node array, each with:
            - team: team slug (from registry)
            - mode: "auto" or "gate"
            - prompt: prompt text for this node
            - timeout: (optional) timeout in seconds
        objective: Overall pipeline objective description
        output_path: (optional) output file path, defaults to
                     .o-team/pipelines/{slug}.yaml

    Returns:
        dict with success status and pipeline info
    """
    # Parse nodes
    try:
        nodes = json.loads(nodes_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}

    if not nodes or not isinstance(nodes, list):
        return {"success": False, "error": "nodes must be a non-empty array"}

    # Load registry for team validation
    utils.ensure_global_dir()
    registry = utils.read_json(utils.REGISTRY_FILE)
    teams_by_slug = {t["slug"]: t for t in registry.get("teams", [])}

    # Validate and build node list
    pipeline_nodes = []
    errors = []

    for i, node in enumerate(nodes):
        team_slug = node.get("team")
        if not team_slug:
            errors.append(f"Node {i+1}: missing 'team' field")
            continue

        team = teams_by_slug.get(team_slug)
        if not team:
            errors.append(
                f"Node {i+1}: team '{team_slug}' not found in registry. "
                f"Available: {', '.join(teams_by_slug.keys())}"
            )
            continue

        # Validate team path still exists
        team_path = Path(team["path"])
        if not team_path.exists():
            errors.append(
                f"Node {i+1}: team '{team_slug}' path no longer exists: {team['path']}"
            )
            continue

        mode = node.get("mode", "gate")
        if mode not in ("auto", "gate"):
            errors.append(f"Node {i+1}: mode must be 'auto' or 'gate', got '{mode}'")
            continue

        node_id = f"{i+1:02d}-{team_slug}"
        prompt = node.get("prompt", "")
        timeout = node.get("timeout", utils.DEFAULT_TIMEOUT)

        pipeline_nodes.append({
            "id": node_id,
            "team": team_slug,
            "team_path": str(team_path),
            "mode": mode,
            "prompt": prompt,
            "timeout": timeout,
        })

    if errors:
        return {"success": False, "errors": errors}

    # Build pipeline data
    slug = utils.slugify(name)
    pipeline_data = {
        "version": "1",
        "name": name,
        "slug": slug,
        "objective": objective,
        "created_at": utils.now_local_iso(),
        "nodes": pipeline_nodes,
    }

    # Determine output path
    if output_path:
        out = utils.resolve_path(output_path)
    else:
        project_dir = utils.ensure_project_dir()
        out = project_dir / utils.PIPELINES_DIR_NAME / f"{slug}.yaml"

    # Write YAML
    utils.write_yaml(out, pipeline_data)

    return {
        "success": True,
        "pipeline": pipeline_data,
        "output_path": str(out),
        "node_count": len(pipeline_nodes),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Create a pipeline YAML")
    parser.add_argument("--name", required=True, help="Pipeline name")
    parser.add_argument("--nodes", required=True, help="JSON array of nodes")
    parser.add_argument("--objective", default="", help="Pipeline objective")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    result = create_pipeline(
        name=args.name,
        nodes_json=args.nodes,
        objective=args.objective,
        output_path=args.output,
    )

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"✅ Pipeline '{args.name}' 已建立")
            print(f"   檔案: {result['output_path']}")
            print(f"   節點: {result['node_count']}")
            for node in result["pipeline"]["nodes"]:
                mode_icon = "⚡" if node["mode"] == "auto" else "⏸"
                print(f"   {mode_icon} {node['id']} ({node['team']})")
        else:
            print(f"❌ 建立失敗")
            for err in result.get("errors", [result.get("error", "Unknown")]):
                print(f"   ✗ {err}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
