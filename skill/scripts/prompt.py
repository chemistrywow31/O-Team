"""O-Team CLI — Shared prompt assembly for pipeline nodes.

Extracts the common prompt-building logic used by both run_pipeline.py
and execute_node.py so each module delegates here instead of duplicating.
"""

import re
from pathlib import Path

from . import utils


NODE_REF_PATTERN = re.compile(r"\{\{\s*node\s*:\s*([a-zA-Z0-9_\-.]+)\s*\}\}")


def expand_node_refs(text: str, sandbox: Path) -> str:
    """Expand {{node:<id>}} tags with the referenced node's output.md content.

    Replaces each tag with <output id="<id>">...</output>. If the referenced
    node has not produced output yet, inserts a placeholder tag so the LLM
    can see the reference but knows the data is missing.
    """
    if not text or "{{" not in text:
        return text

    def _replace(match: re.Match) -> str:
        node_id = match.group(1)
        output_file = sandbox / node_id / "output.md"
        if output_file.exists():
            try:
                content = output_file.read_text(encoding="utf-8").strip()
                return f'<output id="{node_id}">\n{content}\n</output>'
            except Exception:
                return f'<output id="{node_id}" status="read_error"/>'
        return f'<output id="{node_id}" status="not_yet_available"/>'

    return NODE_REF_PATTERN.sub(_replace, text)


def list_workspace_files(workspace: Path) -> list[str]:
    """List files in workspace directory (non-recursive, top level only)."""
    if not workspace.is_dir():
        return []
    files = []
    for item in sorted(workspace.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_file():
            size = item.stat().st_size
            files.append(f"{item.name} ({human_size(size)})")
        elif item.is_dir():
            count = sum(1 for _ in item.rglob("*") if _.is_file())
            files.append(f"{item.name}/ ({count} files)")
    return files


def human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.0f}TB"


def read_entry_skill(office: Path) -> str:
    """Read the boss entry-point skill from a team's office folder.

    Returns the skill content (frontmatter stripped) or empty string.
    """
    boss_skill = office / ".claude" / "skills" / "boss" / "SKILL.md"
    if not boss_skill.exists():
        return ""
    try:
        content = boss_skill.read_text(encoding="utf-8").strip()
        # Strip YAML frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()
        return content
    except Exception:
        return ""


def resolve_prompt_text(node: dict, pipeline_path: Path | None = None) -> str:
    """Resolve the prompt text for a node.

    Prefers inline prompt; falls back to prompt_file.
    """
    prompt_text = node.get("prompt", "").strip()
    if prompt_text:
        return prompt_text

    prompt_file = node.get("prompt_file", "").strip()
    if prompt_file:
        pf = Path(prompt_file)
        if not pf.is_absolute() and pipeline_path:
            pf = (pipeline_path.parent / pf).resolve()
        if pf.exists():
            try:
                return pf.read_text(encoding="utf-8").strip()
            except Exception:
                pass

    return ""


def assemble_prompt(node: dict, sandbox: Path, is_first_node: bool) -> str:
    """Assemble the complete prompt for a node.

    Combines:
    1. Context from input.md (if exists)
    2. Workspace file listing
    3. Team rules from .claude/rules/*.md
    4. Entry skill (for team nodes only — enables coordinator workflow)
    5. Node-specific instructions (from pipeline prompt field or prompt_file)
    6. Output instruction

    Variable data sections are wrapped in XML tags for better Claude parsing.
    """
    office = sandbox / node["id"]
    workspace = sandbox / "workspace"
    is_team_node = bool(node.get("team"))
    parts = []

    # Header
    if is_team_node:
        parts.append(f"# O-Team Pipeline Task")
        parts.append(f"# Node: {node['id']} | Team: {node['team']}")
    else:
        parts.append(f"# O-Team Pipeline Task")
        parts.append(f"# Node: {node['id']} | Prompt Node")
    parts.append("")

    # Context from input.md
    input_file = office / "input.md"
    if input_file.exists():
        input_content = utils.read_text(input_file)
        if input_content.strip():
            if is_first_node:
                parts.append("## Initial Input")
                parts.append("")
                parts.append("<initial_input>")
                parts.append(input_content)
                parts.append("</initial_input>")
            else:
                parts.append("## Context (from previous step)")
                parts.append("")
                parts.append("<previous_output>")
                parts.append(input_content)
                parts.append("</previous_output>")
            parts.append("")

    # Workspace listing
    workspace_files = list_workspace_files(workspace)
    if workspace_files:
        parts.append("## Workspace Files")
        parts.append("The workspace/ directory contains these shared files:")
        parts.append("")
        for wf in workspace_files:
            parts.append(f"- {wf}")
        parts.append("")
        parts.append(f"Workspace path: {workspace}")
        parts.append("")

    # Team rules (from .claude/rules/*.md)
    rules_dir = office / ".claude" / "rules"
    if rules_dir.is_dir():
        rule_files = sorted(rules_dir.glob("*.md"))
        if rule_files:
            parts.append("## Team Rules")
            parts.append("")
            for rf in rule_files:
                try:
                    content = rf.read_text(encoding="utf-8").strip()
                    if content.startswith("---"):
                        end = content.find("---", 3)
                        if end != -1:
                            content = content[end + 3:].strip()
                    if content:
                        parts.append(f"### {rf.stem}")
                        parts.append("")
                        tag_name = rf.stem.replace(" ", "_")
                        parts.append(f"<rule_{tag_name}>")
                        parts.append(content)
                        parts.append(f"</rule_{tag_name}>")
                        parts.append("")
                except Exception:
                    pass

    # Entry skill injection (team nodes only)
    if is_team_node:
        entry_skill = read_entry_skill(office)
        if entry_skill:
            parts.append("## Entry Workflow")
            parts.append("")
            parts.append("Follow this workflow to execute the team's full process:")
            parts.append("")
            parts.append("<entry_skill>")
            parts.append(entry_skill)
            parts.append("</entry_skill>")
            parts.append("")

    # Node-specific instructions
    prompt_text = resolve_prompt_text(node)
    if prompt_text:
        prompt_text = expand_node_refs(prompt_text, sandbox)
        parts.append("## Instructions")
        parts.append("")
        parts.append("<node_instructions>")
        parts.append(prompt_text)
        parts.append("</node_instructions>")
        parts.append("")

    # Output instruction
    parts.append("## Output")
    parts.append("")
    parts.append("Write your primary deliverable to output.md in the current directory.")
    parts.append("Place any supporting files (code, data, diagrams) in the workspace/ directory.")
    parts.append("")

    return "\n".join(parts)
