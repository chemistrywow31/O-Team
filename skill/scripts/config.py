"""O-Team CLI — Configuration management.

Usage:
    python -m scripts.config detect --json     # Detect current statusline state
    python -m scripts.config apply <choice> --json  # Apply statusline choice
    python -m scripts.config show --json       # Show full O-Team config

Statusline choices: o-team, keep, merge
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import utils


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HOME = Path.home()
SETTINGS_PATH = HOME / ".claude" / "settings.json"
O_TEAM_DIR = HOME / ".o-team"
STATUSLINE_SCRIPT = O_TEAM_DIR / "statusline.py"
STATUSLINE_STANDALONE = O_TEAM_DIR / "statusline_standalone.py"
CONFIG_FILE = O_TEAM_DIR / "config.json"


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_statusline() -> dict:
    """Detect current statusline configuration.

    Returns:
        {
            "current": "claude-hud" | "o-team" | "o-team-merged" | "other" | "none",
            "command": "...",  # current command if any
            "has_o_team_scripts": true/false,
            "backup": "..." | null,  # backed up command if any
        }
    """
    result = {
        "current": "none",
        "command": "",
        "has_o_team_scripts": STATUSLINE_SCRIPT.exists() and STATUSLINE_STANDALONE.exists(),
        "backup": None,
    }

    if not SETTINGS_PATH.exists():
        return result

    try:
        settings = json.loads(SETTINGS_PATH.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return result

    cmd = settings.get("statusLine", {}).get("command", "")
    result["command"] = cmd

    # Check backup
    backup = settings.get("_o_team_backup", {}).get("statusLine_command")
    if backup:
        result["backup"] = backup

    if not cmd.strip():
        result["current"] = "none"
    elif "statusline_standalone" in cmd and "o-team" in cmd.lower():
        result["current"] = "o-team"
    elif "claude-hud" in cmd:
        if "--extra-cmd" in cmd and "o-team" in cmd.lower():
            result["current"] = "o-team-merged"
        else:
            result["current"] = "claude-hud"
    else:
        result["current"] = "other"

    return result


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def _find_python() -> str:
    """Find python command."""
    import shutil as sh
    for cmd in ("python3", "python"):
        if sh.which(cmd):
            return cmd
    return "python3"


def apply_statusline(choice: str) -> dict:
    """Apply a statusline configuration choice.

    Args:
        choice: "o-team", "keep", "merge", or "restore"

    Returns:
        { "success": bool, "message": str, "applied": str }
    """
    detection = detect_statusline()
    python_cmd = _find_python()

    if choice == "keep":
        return {
            "success": True,
            "message": "Statusline 保持不變",
            "applied": "keep",
        }

    if choice == "restore":
        backup = detection.get("backup")
        if not backup:
            return {
                "success": False,
                "message": "沒有備份可以還原",
                "applied": "none",
            }
        _update_settings_statusline(backup)
        return {
            "success": True,
            "message": f"已還原為先前的 statusline",
            "applied": "restore",
        }

    if choice == "o-team":
        if not STATUSLINE_STANDALONE.exists():
            return {
                "success": False,
                "message": f"Statusline 腳本不存在: {STATUSLINE_STANDALONE}",
                "applied": "none",
            }
        new_cmd = f"{python_cmd} {STATUSLINE_STANDALONE}"
        _update_settings_statusline(new_cmd)
        return {
            "success": True,
            "message": "已啟用 O-Team 獨立 statusline",
            "applied": "o-team",
        }

    if choice == "merge":
        if detection["current"] not in ("claude-hud", "o-team-merged"):
            return {
                "success": False,
                "message": "Merge 模式需要 claude-hud，但未偵測到",
                "applied": "none",
            }
        if not STATUSLINE_SCRIPT.exists():
            return {
                "success": False,
                "message": f"Extra-cmd 腳本不存在: {STATUSLINE_SCRIPT}",
                "applied": "none",
            }

        current_cmd = detection["command"]
        extra_cmd_arg = f'--extra-cmd "{python_cmd} {STATUSLINE_SCRIPT}"'

        if "--extra-cmd" in current_cmd:
            # Replace existing --extra-cmd
            import re
            new_cmd = re.sub(r'--extra-cmd\s+"[^"]*"', extra_cmd_arg, current_cmd)
        else:
            # Append --extra-cmd to claude-hud command
            if 'index.js"\'' in current_cmd:
                new_cmd = current_cmd.replace(
                    'index.js"\'',
                    f'index.js" {extra_cmd_arg}\''
                )
            elif "index.js'" in current_cmd:
                new_cmd = current_cmd.replace(
                    "index.js'",
                    f"index.js' {extra_cmd_arg}"
                )
            else:
                new_cmd = current_cmd + f" {extra_cmd_arg}"

        _update_settings_statusline(new_cmd)
        return {
            "success": True,
            "message": "已將 O-Team 狀態合併至 claude-hud",
            "applied": "merge",
        }

    return {
        "success": False,
        "message": f"未知的選項: {choice}",
        "applied": "none",
    }


def _update_settings_statusline(new_command: str) -> None:
    """Update settings.json with new statusline command, backing up previous."""
    settings = {}
    if SETTINGS_PATH.exists():
        try:
            settings = json.loads(SETTINGS_PATH.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Backup current command
    prev = settings.get("statusLine", {}).get("command", "")
    if prev and prev != new_command:
        if "_o_team_backup" not in settings:
            settings["_o_team_backup"] = {}
        settings["_o_team_backup"]["statusLine_command"] = prev

    settings["statusLine"] = {
        "type": "command",
        "command": new_command,
    }

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Show config
# ---------------------------------------------------------------------------


def set_language(lang: str) -> dict:
    """Set O-Team language preference.

    Args:
        lang: "en" or "zh-TW"

    Writes to ~/.o-team/config.json.
    """
    valid = {"en", "zh-TW", "zh-tw", "zh", "chinese", "english"}
    normalized = lang.strip().lower()

    if normalized in ("zh-tw", "zh", "chinese"):
        locale = "zh-TW"
    elif normalized in ("en", "english"):
        locale = "en"
    else:
        return {
            "success": False,
            "message": f"Unsupported language: {lang}. Use 'en' or 'zh-TW'.",
        }

    config = {}
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    config["language"] = locale
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    label = "繁體中文" if locale == "zh-TW" else "English"
    return {
        "success": True,
        "language": locale,
        "message": f"Language set to {label}.",
    }


def show_config() -> dict:
    """Show full O-Team configuration."""
    detection = detect_statusline()

    config = {}
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "statusline": detection,
        "global_dir": str(O_TEAM_DIR),
        "registry_exists": (O_TEAM_DIR / "registry.json").exists(),
        "config": config,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="O-Team configuration")
    parser.add_argument("action", choices=["detect", "apply", "show", "set-language"])
    parser.add_argument("choice", nargs="?", default=None,
                        help="For apply: o-team, keep, merge, restore. For set-language: en, zh-TW")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    if args.action == "detect":
        result = detect_statusline()
    elif args.action == "apply":
        if not args.choice:
            parser.error("apply requires a choice: o-team, keep, merge, restore")
        result = apply_statusline(args.choice)
    elif args.action == "set-language":
        if not args.choice:
            parser.error("set-language requires a value: en, zh-TW")
        result = set_language(args.choice)
    elif args.action == "show":
        result = show_config()
    else:
        result = {"error": f"Unknown action: {args.action}"}

    if args.json:
        utils.print_json(result)

    sys.exit(0)


if __name__ == "__main__":
    main()
