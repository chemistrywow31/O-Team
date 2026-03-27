"""O-Team CLI — Internationalization (i18n).

Detects user language from:
  1. ~/.o-team/config.json  → "language" field (user override)
  2. ~/.claude/settings.json → "language" field
  3. LANG / LC_ALL environment variable
  4. Fallback: "en"

Supported locales: en, zh-TW
"""

import json
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_detected_lang: str | None = None


def detect_language() -> str:
    """Detect user language. Returns 'en' or 'zh-TW'."""
    global _detected_lang
    if _detected_lang is not None:
        return _detected_lang

    lang = None
    home = Path.home()

    # 1. O-Team config override
    ot_config = home / ".o-team" / "config.json"
    if ot_config.exists():
        try:
            data = json.loads(ot_config.read_text("utf-8"))
            lang = data.get("language")
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Claude Code settings
    if not lang:
        cc_settings = home / ".claude" / "settings.json"
        if cc_settings.exists():
            try:
                data = json.loads(cc_settings.read_text("utf-8"))
                lang = data.get("language")
            except (json.JSONDecodeError, OSError):
                pass

    # 3. System locale
    if not lang:
        lang = os.environ.get("LANG") or os.environ.get("LC_ALL") or ""

    _detected_lang = _normalize(lang or "")
    return _detected_lang


def _normalize(lang: str) -> str:
    """Normalize language string to supported locale."""
    lang = lang.lower().strip()

    # Chinese variants → zh-TW
    if any(k in lang for k in ("zh", "chinese", "中文", "繁體", "taiwanese")):
        return "zh-TW"

    # Japanese → en (no Japanese support yet, fallback)
    # Everything else → en
    return "en"


def set_language(lang: str) -> None:
    """Override detected language for this session."""
    global _detected_lang
    _detected_lang = _normalize(lang)


# ---------------------------------------------------------------------------
# Translation strings
# ---------------------------------------------------------------------------

_STRINGS: dict[str, dict[str, str]] = {
    # --- Banner ---
    "banner_subtitle": {
        "en": "Multi-team AI Agent Pipeline Orchestrator",
        "zh-TW": "多團隊 AI Agent Pipeline 調度器",
    },

    # --- Config UI ---
    "config_title": {
        "en": "O-Team Settings",
        "zh-TW": "O-Team 設定",
    },
    "config_statusline_label": {
        "en": "Statusline",
        "zh-TW": "Statusline（狀態列）",
    },
    "config_what_to_configure": {
        "en": "What would you like to configure?",
        "zh-TW": "要設定什麼？",
    },
    "config_done": {
        "en": "Done",
        "zh-TW": "完成",
    },
    "config_statusline_setup": {
        "en": "Statusline setup",
        "zh-TW": "Statusline 設定",
    },
    "config_language_setup": {
        "en": "Language / 語系",
        "zh-TW": "語系 / Language",
    },

    # --- Statusline states ---
    "sl_none": {
        "en": "No statusline configured",
        "zh-TW": "未設定 statusline",
    },
    "sl_claude_hud": {
        "en": "claude-hud (merge supported)",
        "zh-TW": "claude-hud（可合併 O-Team 狀態）",
    },
    "sl_merged": {
        "en": "claude-hud + O-Team (merged)",
        "zh-TW": "claude-hud + O-Team（已合併）",
    },
    "sl_o_team": {
        "en": "O-Team standalone statusline",
        "zh-TW": "O-Team 獨立 statusline",
    },
    "sl_other": {
        "en": "Other statusline tool (merge not supported)",
        "zh-TW": "其他 statusline 工具（不支援合併）",
    },

    # --- Statusline options ---
    "opt_merge": {
        "en": "Merge — show O-Team status alongside claude-hud (recommended)",
        "zh-TW": "合併 — 在 claude-hud 旁顯示 O-Team pipeline 狀態（推薦）",
    },
    "opt_replace": {
        "en": "Replace — use O-Team standalone statusline",
        "zh-TW": "替換 — 改用 O-Team 獨立 statusline",
    },
    "opt_keep": {
        "en": "Keep — no changes",
        "zh-TW": "保持 — 不變更",
    },
    "opt_enable": {
        "en": "Enable — use O-Team standalone statusline (recommended)",
        "zh-TW": "啟用 — 使用 O-Team 獨立 statusline（推薦）",
    },
    "opt_skip": {
        "en": "Skip — don't set up statusline",
        "zh-TW": "跳過 — 不設定",
    },
    "opt_restore": {
        "en": "Restore — revert to previous statusline",
        "zh-TW": "還原 — 恢復先前的 statusline",
    },
    "opt_remove_merge": {
        "en": "Remove — revert to plain claude-hud",
        "zh-TW": "移除 — 還原為原本的 claude-hud",
    },

    # --- Config results ---
    "result_applied": {
        "en": "Restart Claude Code to take effect.",
        "zh-TW": "重新啟動 Claude Code 後生效。",
    },
    "result_kept": {
        "en": "Statusline kept as-is.",
        "zh-TW": "Statusline 保持不變。",
    },

    # --- Language options ---
    "lang_en": {
        "en": "English",
        "zh-TW": "English（英文）",
    },
    "lang_zh_tw": {
        "en": "繁體中文 (Traditional Chinese)",
        "zh-TW": "繁體中文",
    },
    "lang_saved": {
        "en": "Language saved.",
        "zh-TW": "語系已儲存。",
    },

    # --- Pipeline status ---
    "pipeline_running": {
        "en": "Running...",
        "zh-TW": "執行中...",
    },
    "pipeline_complete": {
        "en": "Pipeline complete",
        "zh-TW": "Pipeline 完成",
    },
    "pipeline_error": {
        "en": "Error",
        "zh-TW": "錯誤",
    },
    "pipeline_paused": {
        "en": "Waiting for review",
        "zh-TW": "等待審核",
    },
    "pipeline_final_output": {
        "en": "Final output",
        "zh-TW": "最終產出",
    },
    "pipeline_actions": {
        "en": "Actions",
        "zh-TW": "操作",
    },
}


def t(key: str) -> str:
    """Get translated string for current language."""
    lang = detect_language()
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))


def t_with(key: str, lang: str) -> str:
    """Get translated string for a specific language."""
    locale = _normalize(lang)
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(locale, entry.get("en", key))
