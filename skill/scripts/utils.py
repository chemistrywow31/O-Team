"""O-Team CLI shared utilities."""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GLOBAL_DIR = Path.home() / ".o-team"
REGISTRY_FILE = GLOBAL_DIR / "registry.json"
CONFIG_FILE = GLOBAL_DIR / "config.json"
PROJECT_DIR_NAME = ".o-team"
PIPELINES_DIR_NAME = "pipelines"
RUNS_DIR_NAME = "runs"
ARCHIVE_DIR_NAME = "archive"

DEFAULT_TIMEOUT = 1800  # 30 minutes
DEFAULT_COMMAND = "claude -p {prompt_file} --dangerously-skip-permissions"

# ---------------------------------------------------------------------------
# Global directory bootstrap
# ---------------------------------------------------------------------------


def ensure_global_dir() -> Path:
    """Create ~/.o-team/ and default files if they don't exist."""
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        write_json(REGISTRY_FILE, {"teams": []})
    if not CONFIG_FILE.exists():
        write_json(CONFIG_FILE, {
            "default_timeout": DEFAULT_TIMEOUT,
            "default_command": DEFAULT_COMMAND,
        })
    return GLOBAL_DIR


def ensure_project_dir(project_root: Path | None = None) -> Path:
    """Create {project}/.o-team/pipelines/ and runs/ if they don't exist."""
    root = project_root or Path.cwd()
    project_dir = root / PROJECT_DIR_NAME
    (project_dir / PIPELINES_DIR_NAME).mkdir(parents=True, exist_ok=True)
    (project_dir / RUNS_DIR_NAME).mkdir(parents=True, exist_ok=True)
    return project_dir


# ---------------------------------------------------------------------------
# JSON / YAML I/O
# ---------------------------------------------------------------------------


def read_json(path: Path) -> Any:
    """Read and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    """Write data to a JSON file with pretty formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def read_yaml(path: Path) -> Any:
    """Read and parse a YAML file."""
    try:
        import yaml
    except ImportError:
        print_error("PyYAML is required. Install with: pip install pyyaml")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_yaml(path: Path, data: Any) -> None:
    """Write data to a YAML file."""
    try:
        import yaml
    except ImportError:
        print_error("PyYAML is required. Install with: pip install pyyaml")
        sys.exit(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def read_text(path: Path) -> str:
    """Read a text file and return its content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path: Path, content: str) -> None:
    """Write text content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# UUID & naming
# ---------------------------------------------------------------------------


def generate_run_id() -> str:
    """Generate a short UUID for run identification (first 8 chars)."""
    return uuid.uuid4().hex[:8]


def iter_archive_run_dirs(archive_dir: Path):
    """Yield all archived run directories.

    Supports both the legacy flat layout (archive/<name>-<uuid>/) and the
    current date-partitioned layout (archive/YYYY/MM/DD/<name>-<uuid>/).
    A directory is considered a run if it contains a meta.json file.
    """
    if not archive_dir.exists():
        return
    for meta_path in archive_dir.rglob("meta.json"):
        if meta_path.is_file():
            yield meta_path.parent


def find_run_dir(run_id: str, project_dir: Path) -> Path | None:
    """Find a run directory by ID, searching both runs/ and archive/.

    archive/ may be flat (archive/<name>-<uuid>) or date-partitioned
    (archive/YYYY/MM/DD/<name>-<uuid>) — search recursively.

    Returns the Path if found, otherwise None.
    """
    # Direct match in runs/
    direct = project_dir / RUNS_DIR_NAME / run_id
    if direct.exists():
        return direct

    # Recursive search in archive/ for any folder ending with -<run_id>
    archive_dir = project_dir / ARCHIVE_DIR_NAME
    if archive_dir.exists():
        for entry in archive_dir.rglob(f"*-{run_id}"):
            if entry.is_dir():
                return entry

    return None


def slugify(name: str) -> str:
    """Convert a name to kebab-case slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s\-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def now_local_iso() -> str:
    """Return current local time as ISO 8601 string."""
    return datetime.now().astimezone().isoformat()


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"ERROR: {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message to stderr."""
    print(f"WARNING: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def resolve_path(path_str: str) -> Path:
    """Resolve a path string to an absolute Path."""
    return Path(path_str).expanduser().resolve()


def is_subpath(child: Path, parent: Path) -> bool:
    """Check if child is a subpath of parent."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# CLAUDE.md parsing
# ---------------------------------------------------------------------------


def parse_claude_md_title(path: Path) -> str | None:
    """Extract the first H1 title from a CLAUDE.md file."""
    try:
        content = read_text(path)
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return None


def parse_claude_md_preview(path: Path, max_chars: int = 500) -> str:
    """Return the first max_chars characters of a CLAUDE.md file."""
    try:
        content = read_text(path)
        return content[:max_chars]
    except (OSError, UnicodeDecodeError):
        return ""


# ---------------------------------------------------------------------------
# Agent directory scanning
# ---------------------------------------------------------------------------


def count_md_files(directory: Path) -> int:
    """Count .md files in a directory (non-recursive)."""
    if not directory.is_dir():
        return 0
    return sum(1 for f in directory.iterdir() if f.suffix == ".md" and f.is_file())


def count_md_files_recursive(directory: Path) -> int:
    """Count .md files in a directory (recursive)."""
    if not directory.is_dir():
        return 0
    return sum(1 for f in directory.rglob("*.md") if f.is_file())


def list_agents(agents_dir: Path) -> list[str]:
    """List all agent .md files relative to the agents/ directory."""
    if not agents_dir.is_dir():
        return []
    return sorted(
        str(f.relative_to(agents_dir))
        for f in agents_dir.rglob("*.md")
        if f.is_file()
    )


def find_coordinator(agents_dir: Path) -> str | None:
    """Find coordinator .md file at the root of agents/ directory."""
    if not agents_dir.is_dir():
        return None
    for f in agents_dir.iterdir():
        if f.suffix == ".md" and f.is_file():
            return f.name
    return None


def count_skills(skills_dir: Path) -> int:
    """Count skill directories (each containing SKILL.md)."""
    if not skills_dir.is_dir():
        return 0
    return sum(
        1 for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def count_rules(rules_dir: Path) -> int:
    """Count rule .md files (recursive)."""
    return count_md_files_recursive(rules_dir)


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(path: Path) -> dict:
    """Parse YAML-style frontmatter from a .md file. Returns {} on failure."""
    try:
        content = read_text(path)
    except (OSError, UnicodeDecodeError):
        return {}
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    block = content[3:end].strip()
    result: dict = {}
    for line in block.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Entry-point detection (commander skill / coordinator agent)
# ---------------------------------------------------------------------------

ENTRY_SKILL_KEYWORDS = (
    "entry point",
    "entry-point",
    "entrypoint",
    "standard entry",
    "入口",
    "指揮官",
    "spawns the",
    "spawn the",
    "launch the",
    "launches the",
)

COORDINATOR_AGENT_HINTS = (
    "coordinator",
    "boss",
    "lead",
    "orchestrat",
)


def _score_entry_skill(desc: str) -> int:
    """Score a skill description for entry-point likelihood (0 = none)."""
    low = desc.lower()
    score = 0
    for kw in ENTRY_SKILL_KEYWORDS:
        if kw in low:
            score += 2 if kw in ("entry point", "entry-point", "入口") else 1
    return score


def detect_entry_skill(skills_dir: Path) -> dict:
    """Scan .claude/skills/*/SKILL.md for a commander entry skill.

    Returns dict:
        found: bool
        name: str | None      — skill slug (directory name)
        display: str | None   — frontmatter name field
        description: str | None
        ambiguous: bool       — True if >1 plausible candidates
        candidates: list[dict] — all scanned skills with score > 0
    """
    result = {
        "found": False,
        "name": None,
        "display": None,
        "description": None,
        "ambiguous": False,
        "candidates": [],
    }
    if not skills_dir.is_dir():
        return result

    scored = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir():
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        fm = parse_frontmatter(skill_md)
        desc = fm.get("description", "")
        score = _score_entry_skill(desc)
        if score > 0:
            scored.append({
                "slug": d.name,
                "name": fm.get("name", d.name),
                "description": desc,
                "score": score,
            })

    result["candidates"] = scored
    if not scored:
        return result

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[0]
    result["found"] = True
    result["name"] = top["slug"]
    result["display"] = top["name"]
    result["description"] = top["description"]
    result["ambiguous"] = (
        len(scored) > 1 and scored[1]["score"] == top["score"]
    )
    return result


def detect_coordinator_agent(agents_dir: Path) -> dict:
    """Find the coordinator agent (fallback when no entry skill exists).

    Prefers .md files at agents/ root whose filename or frontmatter name
    hints at coordinator/boss/lead. Falls back to the first .md at root.
    Returns dict: found, name (frontmatter name), file (filename), description.
    """
    result = {
        "found": False,
        "name": None,
        "file": None,
        "description": None,
    }
    if not agents_dir.is_dir():
        return result

    root_mds = [
        f for f in sorted(agents_dir.iterdir())
        if f.suffix == ".md" and f.is_file()
    ]
    if not root_mds:
        return result

    def _hint_score(path: Path, fm: dict) -> int:
        stem = path.stem.lower()
        fname = fm.get("name", "").lower()
        desc = fm.get("description", "").lower()
        score = 0
        for hint in COORDINATOR_AGENT_HINTS:
            if hint in stem or hint in fname:
                score += 3
            if hint in desc:
                score += 1
        return score

    scored = []
    for f in root_mds:
        fm = parse_frontmatter(f)
        scored.append((_hint_score(f, fm), f, fm))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_file, top_fm = scored[0]

    # If no hint matches, fall back to first root .md (legacy A-Team convention)
    chosen_file, chosen_fm = (top_file, top_fm) if top_score > 0 else (
        root_mds[0], parse_frontmatter(root_mds[0])
    )

    result["found"] = True
    result["name"] = chosen_fm.get("name") or chosen_file.stem
    result["file"] = chosen_file.name
    result["description"] = chosen_fm.get("description", "")
    return result


def detect_entry_point(team_path: Path) -> dict:
    """Detect how a team should be launched.

    Priority:
      1. Entry skill (/.claude/skills/<name>/SKILL.md with entry-point keywords)
      2. Coordinator agent (.claude/agents/<name>.md at root)
      3. None — bare prompt mode

    Returns dict:
        entry_type: "skill" | "agent" | "none"
        entry_name: str | None — slash-command name OR agent name for Agent tool
        entry_display: str | None — human-readable name
        detection: "auto" | "fallback"
        ambiguous: bool
        skill_candidates: list
    """
    skills_dir = team_path / ".claude" / "skills"
    agents_dir = team_path / ".claude" / "agents"

    skill = detect_entry_skill(skills_dir)
    if skill["found"]:
        return {
            "entry_type": "skill",
            "entry_name": skill["name"],
            "entry_display": skill["display"],
            "entry_description": skill["description"],
            "detection": "auto",
            "ambiguous": skill["ambiguous"],
            "skill_candidates": skill["candidates"],
        }

    agent = detect_coordinator_agent(agents_dir)
    if agent["found"]:
        return {
            "entry_type": "agent",
            "entry_name": agent["name"],
            "entry_display": agent["name"],
            "entry_description": agent["description"],
            "entry_file": agent["file"],
            "detection": "fallback",
            "ambiguous": False,
            "skill_candidates": [],
        }

    return {
        "entry_type": "none",
        "entry_name": None,
        "entry_display": None,
        "entry_description": None,
        "detection": "fallback",
        "ambiguous": False,
        "skill_candidates": [],
    }


def copy_team_config(team_path: Path, office: Path) -> None:
    """Copy CLAUDE.md and .claude/ directory into the office folder."""
    import shutil
    src_claude_md = team_path / "CLAUDE.md"
    if src_claude_md.exists():
        shutil.copy2(src_claude_md, office / "CLAUDE.md")

    src_claude_dir = team_path / ".claude"
    dst_claude_dir = office / ".claude"
    if src_claude_dir.is_dir():
        if dst_claude_dir.exists():
            shutil.rmtree(dst_claude_dir)
        shutil.copytree(src_claude_dir, dst_claude_dir)


def setup_prompt_node(node: dict, office: Path, pipeline_path: Path) -> None:
    """Setup office folder for a prompt-only node (no team).

    Writes identity as CLAUDE.md and copies custom rules if specified.
    Resolves prompt_file content into the node's prompt field.
    """
    import shutil

    # Write identity as CLAUDE.md. Always create the file (even if empty stub)
    # so claude -p does not walk up and pick up unrelated project CLAUDE.md.
    identity = node.get("identity", "").strip()
    if identity:
        write_text(office / "CLAUDE.md", identity)
    else:
        write_text(
            office / "CLAUDE.md",
            "# O-Team Prompt Node\n\n"
            "Follow the instructions provided via the prompt exactly. "
            "Do not look beyond the provided context.\n",
        )

    # Copy custom rules
    rules = node.get("rules", [])
    if rules:
        rules_dir = office / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        for rule_path_str in rules:
            rp = Path(rule_path_str)
            if not rp.is_absolute():
                rp = (pipeline_path.parent / rp).resolve()
            if rp.exists():
                shutil.copy2(rp, rules_dir / rp.name)

    # Resolve prompt_file into prompt
    prompt_file = node.get("prompt_file", "").strip()
    if prompt_file and not node.get("prompt", "").strip():
        pf = Path(prompt_file)
        if not pf.is_absolute():
            pf = (pipeline_path.parent / pf).resolve()
        if pf.exists():
            node["prompt"] = read_text(pf)
            node["_prompt_file_resolved"] = str(pf)
