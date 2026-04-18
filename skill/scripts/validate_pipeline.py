"""O-Team CLI — Pipeline YAML validator.

Usage:
    python -m scripts.validate_pipeline <pipeline-yaml-path> [--json]

Validates a pipeline YAML file for structural correctness,
team reference integrity, and prompt completeness.
"""

import argparse
import re
import sys
from pathlib import Path

from . import utils
from .prompt import NODE_REF_PATTERN, STEP_REF_PATTERN, resolve_prompt_text
from .validate_path import validate_team_path


KNOWN_NODE_FIELDS = {
    "id", "mode", "team", "team_path",
    "prompt", "prompt_file",
    "identity", "rules",
    "model", "effort",
    "timeout",
}

VALID_MODES = {"auto", "gate"}
VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-.]*$")


def _is_prompt_node(node: dict) -> bool:
    """Check if a node is a prompt-only node (no team required)."""
    has_team = bool(node.get("team"))
    has_prompt = bool(str(node.get("prompt", "")).strip())
    has_prompt_file = bool(str(node.get("prompt_file", "")).strip())
    return not has_team and (has_prompt or has_prompt_file)


def _resolve_prompt_file(prompt_file: str, pipeline_path: Path) -> Path:
    """Resolve a prompt_file path relative to the pipeline YAML location."""
    p = Path(prompt_file)
    if p.is_absolute():
        return p
    return (pipeline_path.parent / p).resolve()


def validate_pipeline(pipeline_path_str: str) -> dict:
    """Validate a pipeline YAML file.

    Checks:
    - YAML is parseable and has required fields
    - Team nodes: team slugs exist in registry, team_path valid
    - Prompt nodes: prompt or prompt_file present, prompt_file exists
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

    # Validate top-level field types
    name = pipeline.get("name")
    if not isinstance(name, str) or not name.strip():
        result["issues"].append({
            "check": "name_type",
            "message": f"name 必須是非空字串，目前是: {type(name).__name__}",
        })

    slug = pipeline.get("slug")
    if slug is not None and (not isinstance(slug, str) or not slug.strip()):
        result["issues"].append({
            "check": "slug_type",
            "message": f"slug 如果有提供必須是非空字串",
        })

    objective = pipeline.get("objective")
    if objective is not None and not isinstance(objective, str):
        result["warnings"].append({
            "check": "objective_type",
            "message": f"objective 應為字串，目前是: {type(objective).__name__}",
        })

    # Validate version (accept both "1" and int 1)
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

        # Warn on unknown fields (likely typos)
        for key in node.keys():
            if key not in KNOWN_NODE_FIELDS:
                result["warnings"].append({
                    "check": "unknown_field",
                    "message": f"{node_label}: 未知欄位 '{key}'（可能是拼字錯誤？）",
                })

        is_prompt = _is_prompt_node(node)

        # Check required fields based on node type
        node_id_raw = node.get("id")
        if not node_id_raw:
            result["issues"].append({
                "check": "node_field",
                "message": f"{node_label}: 缺少欄位 'id'",
            })
        elif not isinstance(node_id_raw, str):
            result["issues"].append({
                "check": "node_id_type",
                "message": f"{node_label}: id 必須是字串，目前是 {type(node_id_raw).__name__}",
            })
        elif not ID_PATTERN.match(node_id_raw):
            result["issues"].append({
                "check": "node_id_format",
                "message": f"{node_label}: id '{node_id_raw}' 格式不合（只能包含字母、數字、底線、連字號、點；不可有空白）",
            })

        if not node.get("mode"):
            result["issues"].append({
                "check": "node_field",
                "message": f"{node_label}: 缺少欄位 'mode'",
            })

        # Type-check optional string fields
        for str_field in ("team", "team_path", "prompt", "prompt_file", "identity", "model"):
            val = node.get(str_field)
            if val is not None and not isinstance(val, str):
                result["issues"].append({
                    "check": "node_field_type",
                    "message": f"{node_label}: '{str_field}' 必須是字串，目前是 {type(val).__name__}",
                })

        # Type-check rules (must be list of strings)
        rules = node.get("rules")
        if rules is not None:
            if not isinstance(rules, list):
                result["issues"].append({
                    "check": "node_rules_type",
                    "message": f"{node_label}: rules 必須是陣列，目前是 {type(rules).__name__}",
                })
            else:
                for ri, rule in enumerate(rules):
                    if not isinstance(rule, str):
                        result["issues"].append({
                            "check": "node_rules_item_type",
                            "message": f"{node_label}: rules[{ri}] 必須是字串",
                        })

        # Must have team OR prompt/prompt_file
        has_team = bool(node.get("team"))
        has_prompt = bool(str(node.get("prompt", "")).strip())
        has_prompt_file = bool(str(node.get("prompt_file", "")).strip())
        if not has_team and not has_prompt and not has_prompt_file:
            result["issues"].append({
                "check": "node_source",
                "message": f"{node_label}: 必須有 'team' 或 'prompt'/'prompt_file' 其中之一",
            })

        # Team node: require team_path
        if has_team and not node.get("team_path") and not is_prompt:
            result["issues"].append({
                "check": "node_field",
                "message": f"{node_label}: team node 缺少欄位 'team_path'",
            })

        # Check unique ID
        node_id = node.get("id", "")
        if node_id in seen_ids:
            result["issues"].append({
                "check": "node_id_unique",
                "message": f"{node_label}: 重複的 node ID '{node_id}'",
            })
        seen_ids.add(node_id)

        # Check mode (strict, case-sensitive)
        mode = node.get("mode", "")
        if mode not in VALID_MODES:
            hint = ""
            if isinstance(mode, str) and mode.lower() in VALID_MODES:
                hint = "（注意：mode 要小寫）"
            result["issues"].append({
                "check": "node_mode",
                "message": f"{node_label} ({node_id}): mode 必須是 'auto' 或 'gate'，目前是 '{mode}'{hint}",
            })

        if is_prompt:
            # --- Prompt node validation ---
            if has_prompt_file:
                pf_path = _resolve_prompt_file(node["prompt_file"], pipeline_path)
                if not pf_path.exists():
                    result["issues"].append({
                        "check": "prompt_file_exists",
                        "message": f"{node_label} ({node_id}): prompt_file 不存在: {pf_path}",
                    })

            # Validate rules paths (skip if already flagged as wrong type)
            rules_val = node.get("rules", [])
            if isinstance(rules_val, list):
                for rule_path_str in rules_val:
                    if not isinstance(rule_path_str, str):
                        continue
                    rp = Path(rule_path_str)
                    if not rp.is_absolute():
                        rp = (pipeline_path.parent / rp).resolve()
                    if not rp.exists():
                        result["issues"].append({
                            "check": "rule_file_exists",
                            "message": f"{node_label} ({node_id}): rule 檔案不存在: {rp}",
                        })
        else:
            # --- Team node validation ---
            team_slug = node.get("team", "")
            if team_slug and team_slug not in teams_by_slug:
                result["issues"].append({
                    "check": "team_registered",
                    "message": f"{node_label} ({node_id}): team '{team_slug}' 不在 registry 中",
                })

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

            # Check prompt for team nodes
            if not has_prompt and not has_prompt_file:
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

        # Check model (optional; free-form string, warn if not claude-*)
        model = node.get("model")
        if model is not None:
            if not isinstance(model, str) or not model.strip():
                result["issues"].append({
                    "check": "node_model",
                    "message": f"{node_label} ({node_id}): model 必須是非空字串",
                })
            elif not model.strip().startswith("claude-"):
                result["warnings"].append({
                    "check": "node_model_unknown",
                    "message": f"{node_label} ({node_id}): model '{model}' 不像 Claude 模型 ID（預期以 'claude-' 開頭）",
                })

        # Check effort (optional; must be one of the supported levels)
        effort = node.get("effort")
        if effort is not None:
            if not isinstance(effort, str) or effort not in VALID_EFFORTS:
                hint = ""
                if isinstance(effort, str) and effort.lower() in VALID_EFFORTS:
                    hint = "（注意：effort 要小寫）"
                result["issues"].append({
                    "check": "node_effort",
                    "message": f"{node_label} ({node_id}): effort 必須是 {sorted(VALID_EFFORTS)} 其中之一，目前是 '{effort}'{hint}",
                })

    # Check {{node:<id>}} and {{step:N}} references in prompts
    all_ids = [n.get("id", "") for n in nodes]
    id_set = set(filter(None, all_ids))
    for i, node in enumerate(nodes):
        node_id = node.get("id", "")
        prompt_text = resolve_prompt_text(node, pipeline_path)
        if not prompt_text:
            continue

        # {{node:<id>}}
        for match in NODE_REF_PATTERN.finditer(prompt_text):
            ref_id = match.group(1)
            if ref_id not in id_set:
                result["warnings"].append({
                    "check": "node_ref_unknown",
                    "message": f"Node {i+1} ({node_id}): 引用未知節點 '{{{{node:{ref_id}}}}}'",
                })
                continue
            ref_idx = all_ids.index(ref_id)
            if ref_idx >= i:
                result["warnings"].append({
                    "check": "node_ref_order",
                    "message": f"Node {i+1} ({node_id}): 引用的節點 '{ref_id}' 尚未執行（在自己或之後）",
                })

        # {{step:N}}
        for match in STEP_REF_PATTERN.finditer(prompt_text):
            n = int(match.group(1))
            if n < 1 or n > len(nodes):
                result["warnings"].append({
                    "check": "step_ref_out_of_range",
                    "message": f"Node {i+1} ({node_id}): 引用 '{{{{step:{n}}}}}' 超出範圍（pipeline 只有 {len(nodes)} 步）",
                })
                continue
            if n - 1 >= i:
                result["warnings"].append({
                    "check": "step_ref_order",
                    "message": f"Node {i+1} ({node_id}): 引用第 {n} 步尚未執行（在自己或之後）",
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
