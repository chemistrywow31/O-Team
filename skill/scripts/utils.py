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

    # Write identity as CLAUDE.md
    identity = node.get("identity", "").strip()
    if identity:
        write_text(office / "CLAUDE.md", identity)

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
