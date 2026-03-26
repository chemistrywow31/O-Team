"""O-Team CLI — Path validation for team directories.

Usage:
    python -m scripts.validate_path <path> [--json]

Validates whether a given path is a valid A-Team generated team directory.
Checks structure completeness and reports blocking issues and warnings.
"""

import argparse
import json
import sys
from pathlib import Path

from . import utils


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

def _check_path_exists(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"路徑不存在: {path}"
    return True, ""


def _check_is_directory(path: Path) -> tuple[bool, str]:
    if not path.is_dir():
        return False, f"不是目錄: {path}"
    return True, ""


def _check_has_claude_md(path: Path) -> tuple[bool, str]:
    if not (path / "CLAUDE.md").exists():
        return False, "缺少 CLAUDE.md — 不是合法團隊根目錄"
    return True, ""


def _check_has_claude_dir(path: Path) -> tuple[bool, str]:
    if not (path / ".claude").is_dir():
        return False, "缺少 .claude/ 目錄"
    return True, ""


def _check_has_agents_dir(path: Path) -> tuple[bool, str]:
    agents_dir = path / ".claude" / "agents"
    if not agents_dir.is_dir():
        return False, "缺少 .claude/agents/ 目錄"
    return True, ""


def _check_has_agent_files(path: Path) -> tuple[bool, str]:
    agents_dir = path / ".claude" / "agents"
    if utils.count_md_files_recursive(agents_dir) == 0:
        return False, ".claude/agents/ 內無 .md 檔案"
    return True, ""


BLOCKING_CHECKS = [
    _check_path_exists,
    _check_is_directory,
    _check_has_claude_md,
    _check_has_claude_dir,
    _check_has_agents_dir,
    _check_has_agent_files,
]


def _warn_has_coordinator(path: Path) -> tuple[bool, str]:
    agents_dir = path / ".claude" / "agents"
    coordinator = utils.find_coordinator(agents_dir)
    if coordinator is None:
        return False, "agents/ 根目錄無 coordinator .md（僅子目錄有檔案）"
    return True, ""


def _warn_has_skills_dir(path: Path) -> tuple[bool, str]:
    if not (path / ".claude" / "skills").is_dir():
        return False, "無 .claude/skills/ 目錄"
    return True, ""


def _warn_has_rules_dir(path: Path) -> tuple[bool, str]:
    if not (path / ".claude" / "rules").is_dir():
        return False, "無 .claude/rules/ 目錄"
    return True, ""


def _warn_is_symlink(path: Path) -> tuple[bool, str]:
    if path.is_symlink():
        target = path.resolve()
        return False, f"路徑是 symlink，實際指向 {target}"
    return True, ""


def _warn_duplicate_registry(path: Path) -> tuple[bool, str]:
    """Check if this path is already registered."""
    utils.ensure_global_dir()
    if not utils.REGISTRY_FILE.exists():
        return True, ""
    registry = utils.read_json(utils.REGISTRY_FILE)
    abs_path = str(path.resolve())
    for team in registry.get("teams", []):
        if team.get("path") == abs_path:
            return False, f"此團隊已在 registry 中註冊 (slug: {team.get('slug', '?')})"
    return True, ""


WARNING_CHECKS = [
    _warn_has_coordinator,
    _warn_has_skills_dir,
    _warn_has_rules_dir,
    _warn_is_symlink,
    _warn_duplicate_registry,
]


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------


def validate_team_path(path_str: str) -> dict:
    """Validate a path as a team directory.

    Returns a dict with:
        valid: bool
        path: str (absolute)
        issues: list[dict] (blocking)
        warnings: list[dict] (non-blocking)
        meta: dict | None (team metadata if valid)
    """
    path = utils.resolve_path(path_str)
    result = {
        "valid": False,
        "path": str(path),
        "issues": [],
        "warnings": [],
        "meta": None,
    }

    # Run blocking checks — stop at first failure
    for check_fn in BLOCKING_CHECKS:
        passed, message = check_fn(path)
        if not passed:
            result["issues"].append({
                "check": check_fn.__name__.replace("_check_", ""),
                "message": message,
            })
            return result

    # All blocking checks passed
    result["valid"] = True

    # Run warning checks
    for check_fn in WARNING_CHECKS:
        passed, message = check_fn(path)
        if not passed:
            result["warnings"].append({
                "check": check_fn.__name__.replace("_warn_", ""),
                "message": message,
            })

    # Extract metadata
    claude_md_path = path / "CLAUDE.md"
    agents_dir = path / ".claude" / "agents"
    skills_dir = path / ".claude" / "skills"
    rules_dir = path / ".claude" / "rules"

    result["meta"] = {
        "name": utils.parse_claude_md_title(claude_md_path) or path.name,
        "claude_md_preview": utils.parse_claude_md_preview(claude_md_path),
        "agents": utils.list_agents(agents_dir),
        "agent_count": utils.count_md_files_recursive(agents_dir),
        "skill_count": utils.count_skills(skills_dir),
        "rule_count": utils.count_rules(rules_dir),
        "coordinator": utils.find_coordinator(agents_dir),
    }

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Validate a team directory path"
    )
    parser.add_argument("path", help="Path to the team directory")
    parser.add_argument(
        "--json", action="store_true", default=False,
        help="Output as JSON"
    )
    args = parser.parse_args()

    result = validate_team_path(args.path)

    if args.json:
        utils.print_json(result)
    else:
        _print_human(result)

    sys.exit(0 if result["valid"] else 1)


def _print_human(result: dict) -> None:
    """Print validation result in human-readable format."""
    path = result["path"]
    valid = result["valid"]

    if valid:
        meta = result["meta"]
        print(f"✅ {path}")
        print(f"   名稱: {meta['name']}")
        print(f"   Agents: {meta['agent_count']}  Skills: {meta['skill_count']}  Rules: {meta['rule_count']}")
        if meta["coordinator"]:
            print(f"   Coordinator: {meta['coordinator']}")
        else:
            print("   Coordinator: (未偵測到)")
        for w in result["warnings"]:
            print(f"   ⚠️  {w['message']}")
    else:
        print(f"❌ {path}")
        for issue in result["issues"]:
            print(f"   ✗ {issue['message']}")


if __name__ == "__main__":
    main()
