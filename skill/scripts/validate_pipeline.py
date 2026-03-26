"""O-Team CLI — Pipeline YAML validator.

Usage:
    python -m scripts.validate_pipeline <pipeline-yaml-path> [--json]

Validates a pipeline YAML file for structural correctness,
team reference integrity, and prompt completeness.
"""

import argparse
import sys
from pathlib import Path

from . import utils
from .validate_path import validate_team_path


def validate_pipeline(pipeline_path_str: str) -> dict:
    """Validate a pipeline YAML file.

    Checks:
    - YAML is parseable and has required fields
    - All team slugs exist in registry
    - All team_path directories still exist and are valid
    - All nodes have non-empty prompts
    - Mode values are valid
    - Node IDs are unique

    Returns dict with:
        valid: bool
        issues: list[dict] (blocking)
        warnings: list[dict] (non-blocking)
        pipeline: dict | None (parsed pipeline if valid YAML)
    """
    pipeline_path = utils.resolve_path(pipeline_path_str)
    result = {
        "valid": False,
        "path": str(pipeline_path),
        "issues": [],
        "warnings": [],
        "pipeline": None,
    }

    # Check file exists
    if not pipeline_path.exists():
        result["issues"].append({
            "check": "file_exists",
            "message": f"Pipeline 檔案不存在: {pipeline_path}",
        })
        return result

    # Parse YAML
    try:
        pipeline = utils.read_yaml(pipeline_path)
    except Exception as e:
        result["issues"].append({
            "check": "yaml_parse",
            "message": f"YAML 解析失敗: {e}",
        })
        return result

    if not isinstance(pipeline, dict):
        result["issues"].append({
            "check": "yaml_structure",
            "message": "Pipeline YAML 必須是一個 mapping (dict)",
        })
        return result

    result["pipeline"] = pipeline

    # Check required top-level fields
    required_fields = ["version", "name", "nodes"]
    for field in required_fields:
        if field not in pipeline:
            result["issues"].append({
                "check": "required_field",
                "message": f"缺少必要欄位: {field}",
            })

    if result["issues"]:
        return result

    # Validate version
    if str(pipeline.get("version")) != "1":
        result["warnings"].append({
            "check": "version",
            "message": f"未知版本: {pipeline.get('version')} (預期 '1')",
        })

    # Validate nodes
    nodes = pipeline.get("nodes", [])
    if not isinstance(nodes, list) or len(nodes) == 0:
        result["issues"].append({
            "check": "nodes_empty",
            "message": "nodes 必須是非空陣列",
        })
        return result

    # Load registry
    utils.ensure_global_dir()
    registry = utils.read_json(utils.REGISTRY_FILE)
    teams_by_slug = {t["slug"]: t for t in registry.get("teams", [])}

    seen_ids = set()
    for i, node in enumerate(nodes):
        node_label = f"Node {i+1}"

        if not isinstance(node, dict):
            result["issues"].append({
                "check": "node_type",
                "message": f"{node_label}: 必須是 mapping (dict)",
            })
            continue

        # Check required node fields
        for field in ["id", "team", "team_path", "mode"]:
            if field not in node:
                result["issues"].append({
                    "check": "node_field",
                    "message": f"{node_label}: 缺少欄位 '{field}'",
                })

        # Check unique ID
        node_id = node.get("id", "")
        if node_id in seen_ids:
            result["issues"].append({
                "check": "node_id_unique",
                "message": f"{node_label}: 重複的 node ID '{node_id}'",
            })
        seen_ids.add(node_id)

        # Check mode
        mode = node.get("mode", "")
        if mode not in ("auto", "gate"):
            result["issues"].append({
                "check": "node_mode",
                "message": f"{node_label} ({node_id}): mode 必須是 'auto' 或 'gate'，目前是 '{mode}'",
            })

        # Check team in registry
        team_slug = node.get("team", "")
        if team_slug and team_slug not in teams_by_slug:
            result["issues"].append({
                "check": "team_registered",
                "message": f"{node_label} ({node_id}): team '{team_slug}' 不在 registry 中",
            })

        # Check team_path exists and is valid
        team_path = node.get("team_path", "")
        if team_path:
            path_obj = Path(team_path)
            if not path_obj.exists():
                result["issues"].append({
                    "check": "team_path_exists",
                    "message": f"{node_label} ({node_id}): team_path 不存在: {team_path}",
                })
            elif not (path_obj / "CLAUDE.md").exists():
                result["issues"].append({
                    "check": "team_path_valid",
                    "message": f"{node_label} ({node_id}): team_path 缺少 CLAUDE.md: {team_path}",
                })

        # Check prompt
        prompt = node.get("prompt", "")
        if not prompt or not prompt.strip():
            result["warnings"].append({
                "check": "node_prompt",
                "message": f"{node_label} ({node_id}): prompt 為空，執行時將只依賴團隊 CLAUDE.md",
            })

        # Check timeout
        timeout = node.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                result["warnings"].append({
                    "check": "node_timeout",
                    "message": f"{node_label} ({node_id}): timeout 值無效 ({timeout})，將使用預設 1800",
                })

    # Final verdict
    result["valid"] = len(result["issues"]) == 0
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Validate a pipeline YAML")
    parser.add_argument("path", help="Path to pipeline YAML file")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    result = validate_pipeline(args.path)

    if args.json:
        utils.print_json(result)
    else:
        _print_human(result)

    sys.exit(0 if result["valid"] else 1)


def _print_human(result: dict) -> None:
    """Print validation result in human-readable format."""
    if result["valid"]:
        pipeline = result["pipeline"]
        node_count = len(pipeline.get("nodes", []))
        print(f"✅ Pipeline '{pipeline.get('name', '?')}' 驗證通過")
        print(f"   節點: {node_count}")
        for w in result["warnings"]:
            print(f"   ⚠️  {w['message']}")
    else:
        print(f"❌ Pipeline 驗證失敗: {result['path']}")
        for issue in result["issues"]:
            print(f"   ✗ {issue['message']}")
        for w in result["warnings"]:
            print(f"   ⚠️  {w['message']}")


if __name__ == "__main__":
    main()
