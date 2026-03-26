"""O-Team CLI — Team registry management.

Usage:
    python -m scripts.registry add <path> [--json]
    python -m scripts.registry remove <slug> [--json]
    python -m scripts.registry list [--json]

Manages the global team registry at ~/.o-team/registry.json.
Supports single team directory and multi-team directory (auto-scan).
"""

import argparse
import sys
from pathlib import Path

from . import utils
from .validate_path import validate_team_path


# ---------------------------------------------------------------------------
# Registry operations
# ---------------------------------------------------------------------------


def _load_registry() -> dict:
    """Load registry from disk, creating if needed."""
    utils.ensure_global_dir()
    return utils.read_json(utils.REGISTRY_FILE)


def _save_registry(registry: dict) -> None:
    """Save registry to disk."""
    utils.write_json(utils.REGISTRY_FILE, registry)


def _find_team_by_slug(registry: dict, slug: str) -> dict | None:
    """Find a team entry by slug."""
    for team in registry.get("teams", []):
        if team.get("slug") == slug:
            return team
    return None


def _find_team_by_path(registry: dict, abs_path: str) -> dict | None:
    """Find a team entry by absolute path."""
    for team in registry.get("teams", []):
        if team.get("path") == abs_path:
            return team
    return None


def _detect_mode(path: Path) -> str:
    """Detect whether path is a single team or multi-team directory.

    Returns: 'single', 'multi', or 'invalid'
    """
    if not path.exists() or not path.is_dir():
        return "invalid"
    if (path / "CLAUDE.md").exists():
        return "single"
    return "multi"


def _scan_multi_dir(path: Path) -> dict:
    """Scan a multi-team directory for valid team subdirectories.

    Returns dict with:
        candidates: list of validation results for dirs WITH CLAUDE.md
        warnings: list of subdirs WITHOUT CLAUDE.md (reported, not skipped)
        total_subdirs: int
    """
    candidates = []
    warnings = []
    subdirs = sorted(
        d for d in path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    for subdir in subdirs:
        if (subdir / "CLAUDE.md").exists():
            result = validate_team_path(str(subdir))
            candidates.append(result)
        else:
            warnings.append({
                "path": str(subdir),
                "message": f"子目錄 {subdir.name}/ 無 CLAUDE.md，不是合法團隊",
            })

    return {
        "candidates": candidates,
        "warnings": warnings,
        "total_subdirs": len(subdirs),
    }


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------


def add_team(path_str: str) -> dict:
    """Add a team or scan a multi-team directory.

    For single team: validates and adds to registry.
    For multi-team directory: scans subdirectories, returns candidates
    for user selection (does not auto-register all).

    Returns dict with operation result.
    """
    path = utils.resolve_path(path_str)
    mode = _detect_mode(path)

    if mode == "invalid":
        return {
            "success": False,
            "mode": "invalid",
            "error": f"路徑不存在或不是目錄: {path}",
        }

    if mode == "single":
        return _add_single_team(path)

    # Multi-team directory
    return _scan_for_candidates(path)


def _add_single_team(path: Path) -> dict:
    """Validate and register a single team directory."""
    validation = validate_team_path(str(path))

    if not validation["valid"]:
        return {
            "success": False,
            "mode": "single",
            "validation": validation,
            "error": "團隊驗證失敗",
        }

    registry = _load_registry()
    abs_path = str(path.resolve())

    # Check for duplicate
    existing = _find_team_by_path(registry, abs_path)
    if existing:
        return {
            "success": False,
            "mode": "single",
            "error": f"此路徑已註冊 (slug: {existing['slug']})",
            "existing": existing,
        }

    # Create registry entry (summary/capabilities will be filled by Claude)
    meta = validation["meta"]
    slug = utils.slugify(meta["name"])

    # Ensure unique slug
    base_slug = slug
    counter = 1
    while _find_team_by_slug(registry, slug):
        slug = f"{base_slug}-{counter}"
        counter += 1

    entry = {
        "slug": slug,
        "path": abs_path,
        "name": meta["name"],
        "summary": "",  # To be filled by Claude (sonnet) after registration
        "capabilities": [],  # To be filled by Claude (sonnet) after registration
        "agent_count": meta["agent_count"],
        "skill_count": meta["skill_count"],
        "rule_count": meta["rule_count"],
        "coordinator": meta["coordinator"],
        "registered_at": utils.now_iso(),
    }

    registry["teams"].append(entry)
    _save_registry(registry)

    return {
        "success": True,
        "mode": "single",
        "team": entry,
        "validation": validation,
    }


def _scan_for_candidates(path: Path) -> dict:
    """Scan multi-team directory and return candidates for selection."""
    scan_result = _scan_multi_dir(path)

    return {
        "success": True,
        "mode": "multi",
        "scan_path": str(path),
        "candidates": scan_result["candidates"],
        "warnings": scan_result["warnings"],
        "total_subdirs": scan_result["total_subdirs"],
        "valid_count": sum(1 for c in scan_result["candidates"] if c["valid"]),
    }


def register_selected(paths: list[str]) -> dict:
    """Register multiple team paths (from multi-dir selection).

    Returns dict with results for each path.
    """
    results = []
    for path_str in paths:
        result = _add_single_team(utils.resolve_path(path_str))
        results.append(result)

    return {
        "total": len(results),
        "registered": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Remove
# ---------------------------------------------------------------------------


def remove_team(slug: str) -> dict:
    """Remove a team from the registry by slug."""
    registry = _load_registry()
    team = _find_team_by_slug(registry, slug)

    if not team:
        return {
            "success": False,
            "error": f"找不到 slug 為 '{slug}' 的團隊",
        }

    registry["teams"] = [t for t in registry["teams"] if t["slug"] != slug]
    _save_registry(registry)

    return {
        "success": True,
        "removed": team,
    }


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def list_teams() -> dict:
    """List all registered teams."""
    registry = _load_registry()
    teams = registry.get("teams", [])

    return {
        "total": len(teams),
        "teams": teams,
    }


# ---------------------------------------------------------------------------
# Update (for Claude to fill summary/capabilities after registration)
# ---------------------------------------------------------------------------


def update_team(slug: str, updates: dict) -> dict:
    """Update a team's metadata (summary, capabilities, etc.)."""
    registry = _load_registry()
    team = _find_team_by_slug(registry, slug)

    if not team:
        return {
            "success": False,
            "error": f"找不到 slug 為 '{slug}' 的團隊",
        }

    allowed_fields = {"summary", "capabilities", "name"}
    for key, value in updates.items():
        if key in allowed_fields:
            team[key] = value

    _save_registry(registry)

    return {
        "success": True,
        "team": team,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="O-Team team registry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_parser = subparsers.add_parser("add", help="Register a team directory")
    add_parser.add_argument("path", help="Path to team directory or multi-team directory")
    add_parser.add_argument("--json", action="store_true", default=False)

    # register-selected (for multi-dir follow-up)
    sel_parser = subparsers.add_parser("register-selected",
                                        help="Register selected paths from multi-dir scan")
    sel_parser.add_argument("paths", nargs="+", help="Paths to register")
    sel_parser.add_argument("--json", action="store_true", default=False)

    # remove
    rm_parser = subparsers.add_parser("remove", help="Remove a team by slug")
    rm_parser.add_argument("slug", help="Team slug to remove")
    rm_parser.add_argument("--json", action="store_true", default=False)

    # list
    ls_parser = subparsers.add_parser("list", help="List all registered teams")
    ls_parser.add_argument("--json", action="store_true", default=False)

    # update (for Claude to fill summary/capabilities)
    up_parser = subparsers.add_parser("update", help="Update team metadata")
    up_parser.add_argument("slug", help="Team slug to update")
    up_parser.add_argument("--summary", help="Team summary")
    up_parser.add_argument("--capabilities", help="Comma-separated capabilities")
    up_parser.add_argument("--json", action="store_true", default=False)

    args = parser.parse_args()

    if args.command == "add":
        result = add_team(args.path)
    elif args.command == "register-selected":
        result = register_selected(args.paths)
    elif args.command == "remove":
        result = remove_team(args.slug)
    elif args.command == "list":
        result = list_teams()
    elif args.command == "update":
        updates = {}
        if args.summary:
            updates["summary"] = args.summary
        if args.capabilities:
            updates["capabilities"] = [c.strip() for c in args.capabilities.split(",")]
        result = update_team(args.slug, updates)
    else:
        parser.print_help()
        sys.exit(1)

    if args.json:
        utils.print_json(result)
    else:
        _print_human(args.command, result)

    if not result.get("success", True):
        sys.exit(1)


def _print_human(command: str, result: dict) -> None:
    """Print operation result in human-readable format."""
    if command == "add":
        if result.get("mode") == "single":
            if result["success"]:
                team = result["team"]
                print(f"✅ 已註冊: {team['name']} (slug: {team['slug']})")
                print(f"   路徑: {team['path']}")
                print(f"   Agents: {team['agent_count']}  Skills: {team['skill_count']}  Rules: {team['rule_count']}")
                validation = result.get("validation", {})
                for w in validation.get("warnings", []):
                    print(f"   ⚠️  {w['message']}")
            else:
                print(f"❌ 註冊失敗: {result.get('error', 'Unknown error')}")
        elif result.get("mode") == "multi":
            print(f"📂 掃描 {result['scan_path']}")
            print(f"   子目錄: {result['total_subdirs']}  合法團隊: {result['valid_count']}")
            for c in result["candidates"]:
                if c["valid"]:
                    meta = c["meta"]
                    print(f"   ✅ {c['path']} — {meta['name']} (agents: {meta['agent_count']})")
                else:
                    print(f"   ❌ {c['path']}")
                    for issue in c["issues"]:
                        print(f"      ✗ {issue['message']}")
            for w in result["warnings"]:
                print(f"   ⚠️  {w['message']}")
        else:
            print(f"❌ {result.get('error', 'Unknown error')}")

    elif command == "register-selected":
        print(f"註冊結果: {result['registered']}/{result['total']} 成功")
        for r in result["results"]:
            if r["success"]:
                print(f"   ✅ {r['team']['name']} (slug: {r['team']['slug']})")
            else:
                print(f"   ❌ {r.get('error', 'Unknown error')}")

    elif command == "remove":
        if result["success"]:
            removed = result["removed"]
            print(f"✅ 已移除: {removed['name']} (slug: {removed['slug']})")
        else:
            print(f"❌ {result.get('error', 'Unknown error')}")

    elif command == "list":
        teams = result["teams"]
        if not teams:
            print("(無已註冊團隊)")
            return
        print(f"已註冊團隊 ({result['total']}):\n")
        for i, team in enumerate(teams, 1):
            summary = team.get("summary", "(未定義)")
            print(f"  [{i}] {team['slug']}")
            print(f"      名稱: {team['name']}")
            print(f"      路徑: {team['path']}")
            print(f"      摘要: {summary}")
            caps = team.get("capabilities", [])
            if caps:
                print(f"      能力: {', '.join(caps)}")
            print(f"      Agents: {team['agent_count']}  Skills: {team.get('skill_count', 0)}  Rules: {team.get('rule_count', 0)}")
            print()

    elif command == "update":
        if result["success"]:
            team = result["team"]
            print(f"✅ 已更新: {team['name']} (slug: {team['slug']})")
        else:
            print(f"❌ {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
