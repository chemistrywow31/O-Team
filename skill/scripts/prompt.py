"""O-Team CLI — Shared prompt assembly for pipeline nodes.

Extracts the common prompt-building logic used by both run_pipeline.py
and execute_node.py so each module delegates here instead of duplicating.
"""

from pathlib import Path

from . import utils


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


def assemble_prompt(node: dict, sandbox: Path, is_first_node: bool) -> str:
    """Assemble the complete prompt for a node.

    Combines:
    1. Context from input.md (if exists)
    2. Workspace file listing
    3. Team rules from .claude/rules/*.md
    4. Node-specific instructions (from pipeline prompt field)
    5. Output instruction

    Variable data sections are wrapped in XML tags for better Claude parsing.
    """
    office = sandbox / node["id"]
    workspace = sandbox / "workspace"
    parts = []

    # Header
    parts.append(f"# O-Team Pipeline Task")
    parts.append(f"# Node: {node['id']} | Team: {node['team']}")
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

    # Node-specific instructions
    prompt_text = node.get("prompt", "")
    if prompt_text and prompt_text.strip():
        parts.append("## Instructions")
        parts.append("")
        parts.append("<node_instructions>")
        parts.append(prompt_text.strip())
        parts.append("</node_instructions>")
        parts.append("")

    # Output instruction
    parts.append("## Output")
    parts.append("")
    parts.append("Write your primary deliverable to output.md in the current directory.")
    parts.append("Place any supporting files (code, data, diagrams) in the workspace/ directory.")
    parts.append("")

    return "\n".join(parts)
