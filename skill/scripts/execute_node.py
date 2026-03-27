"""O-Team CLI — Execute a single pipeline node.

Usage:
    python -m scripts.execute_node <sandbox-path> <node-index> [--json]

Assembles the prompt, runs claude -p with stream-json parsing,
updates status.json for live monitoring. Returns result when done.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import utils
from .stream_parser import (
    StreamParser,
    StatusSnapshot,
    CompleteMessage,
    StreamMessage,
    format_status_line,
    is_complete,
    write_status,
    clear_status,
    STATUS_FILE_NAME,
)


# ---------------------------------------------------------------------------
# Prompt assembly (self-contained, no dependency on run_pipeline.py)
# ---------------------------------------------------------------------------


def _assemble_prompt(node: dict, sandbox: Path, is_first_node: bool) -> str:
    """Assemble the complete prompt for a node."""
    office = sandbox / node["id"]
    workspace = sandbox / "workspace"
    parts: list[str] = []

    # Header
    parts.append(f"# O-Team Pipeline Task")
    parts.append(f"# Node: {node['id']} | Team: {node['team']}")
    parts.append("")

    # Context from input.md
    input_file = office / "input.md"
    if input_file.exists():
        input_content = utils.read_text(input_file)
        if input_content.strip():
            label = "## Initial Input" if is_first_node else "## Context (from previous step)"
            parts.append(label)
            parts.append("")
            parts.append(input_content)
            parts.append("")

    # Workspace listing
    if workspace.is_dir():
        files = []
        for item in sorted(workspace.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_file():
                size = item.stat().st_size
                unit = "B"
                for u in ("KB", "MB", "GB"):
                    if size >= 1024:
                        size /= 1024
                        unit = u
                files.append(f"{item.name} ({size:.0f}{unit})")
            elif item.is_dir():
                count = sum(1 for _ in item.rglob("*") if _.is_file())
                files.append(f"{item.name}/ ({count} files)")
        if files:
            parts.append("## Workspace Files")
            parts.append("The workspace/ directory contains these shared files:")
            parts.append("")
            for f in files:
                parts.append(f"- {f}")
            parts.append("")
            parts.append(f"Workspace path: {workspace}")
            parts.append("")

    # Node-specific instructions
    prompt_text = node.get("prompt", "")
    if prompt_text and prompt_text.strip():
        parts.append("## Instructions")
        parts.append("")
        parts.append(prompt_text.strip())
        parts.append("")

    # Output instruction
    parts.append("## Output")
    parts.append("")
    parts.append("Write your primary deliverable to output.md in the current directory.")
    parts.append("Place any supporting files (code, data, diagrams) in the workspace/ directory.")
    parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Node execution
# ---------------------------------------------------------------------------


def execute_node(sandbox_path: str, node_index: int) -> dict:
    """Execute a single pipeline node.

    Updates meta.json state and writes status.json for live monitoring.
    Returns result dict with success, exit_code, cost, duration, etc.
    """
    sandbox = Path(sandbox_path)
    meta = utils.read_json(sandbox / "meta.json")

    nodes = meta["nodes"]
    if node_index < 0 or node_index >= len(nodes):
        return {"success": False, "error": f"Invalid node index: {node_index}"}

    node = nodes[node_index]
    office = sandbox / node["id"]

    # Mark running
    node["state"] = "RUNNING"
    node["started_at"] = utils.now_iso()
    meta["current_node_index"] = node_index
    meta["state"] = "RUNNING"
    utils.write_json(sandbox / "meta.json", meta)

    # Assemble prompt
    is_first = (node_index == 0)
    prompt_content = _assemble_prompt(node, sandbox, is_first)

    # Write prompt.md for audit trail
    utils.write_text(office / "prompt.md", prompt_content)

    # Paths
    project_status_path = sandbox.parent.parent / STATUS_FILE_NAME
    log_file = office / "run.log"
    events_file = office / "events.jsonl"

    # Status snapshot
    parser = StreamParser()
    status = StatusSnapshot(
        run_id=meta["run_id"],
        pipeline_name=meta.get("pipeline_name", ""),
        node_id=node["id"],
        node_index=node_index,
        total_nodes=len(nodes),
        team=node["team"],
        phase="running",
    )

    # Build command
    cmd = [
        "claude",
        "-p", prompt_content,
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
    ]

    start_time = time.time()
    exit_code = 1
    result_text = ""

    try:
        with open(log_file, "w", encoding="utf-8") as log_f, \
             open(events_file, "w", encoding="utf-8") as evt_f:

            process = subprocess.Popen(
                cmd,
                cwd=str(office),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in process.stdout:
                evt_f.write(line)
                evt_f.flush()

                msg = parser.parse_line(line)

                if is_complete(msg):
                    cm: CompleteMessage = msg
                    result_text = cm.result
                    status.phase = "error" if cm.is_error else "complete"
                    status.cost_usd = cm.cost_usd
                    status.duration_ms = cm.duration_ms
                    status.num_turns = cm.num_turns
                    status.tool_name = ""
                    status.agent_name = ""
                    log_f.write(f"\n--- result ---\n{cm.result}\n")
                    log_f.flush()
                    _update_status(status, project_status_path)

                elif isinstance(msg, list):
                    for m in msg:
                        _process_stream_msg(m, status, log_f)
                    _update_status(status, project_status_path)

                elif isinstance(msg, StreamMessage):
                    _process_stream_msg(msg, status, log_f)
                    _update_status(status, project_status_path)

                # Agent events
                agent_evt = parser.parse_agent_event(line)
                if agent_evt is not None:
                    if agent_evt.kind == "agent_spawn" and agent_evt.agent_name:
                        status.phase = "agent"
                        status.agent_name = agent_evt.agent_name
                        status.agent_description = agent_evt.description
                        log_f.write(f"[agent:spawn] {agent_evt.agent_name} ({agent_evt.agent_type})\n")
                        log_f.flush()
                        _update_status(status, project_status_path)
                    elif agent_evt.kind == "agent_progress":
                        if agent_evt.last_tool:
                            status.tool_name = agent_evt.last_tool
                        if agent_evt.description:
                            status.agent_description = agent_evt.description
                        log_f.write(f"[agent:progress] {agent_evt.agent_name or agent_evt.task_id} tool={agent_evt.last_tool}\n")
                        log_f.flush()
                        _update_status(status, project_status_path)
                    elif agent_evt.kind == "agent_complete":
                        status.phase = "running"
                        status.agent_name = ""
                        status.agent_description = ""
                        log_f.write(f"[agent:complete] {agent_evt.agent_name or agent_evt.task_id} status={agent_evt.status}\n")
                        log_f.flush()
                        _update_status(status, project_status_path)

            process.wait()
            exit_code = process.returncode

    except FileNotFoundError:
        sys.stderr.write("ERROR: 'claude' command not found.\n")
        exit_code = 127
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        exit_code = 130

    elapsed = time.time() - start_time

    # Update meta
    node["exit_code"] = exit_code
    node["finished_at"] = utils.now_iso()
    if exit_code != 0:
        node["state"] = "ERROR"
        node["error"] = f"Exit code: {exit_code}"
        meta["state"] = "ERROR"
    # Don't set COMPLETE — let complete_node.py handle that

    utils.write_json(sandbox / "meta.json", meta)
    clear_status(project_status_path)

    return {
        "success": exit_code == 0,
        "node_id": node["id"],
        "team": node["team"],
        "mode": node["mode"],
        "exit_code": exit_code,
        "duration_seconds": round(elapsed, 1),
        "cost_usd": status.cost_usd,
        "num_turns": status.num_turns,
        "has_output": (office / "output.md").exists(),
    }


def _process_stream_msg(msg: StreamMessage, status: StatusSnapshot, log_f) -> None:
    """Update status and log from a stream message."""
    if msg.content_type == "text" and msg.text:
        status.phase = "running"
        status.tool_name = ""
        status.last_text_preview = msg.text.strip()[:80]
        log_f.write(msg.text)
        log_f.flush()
    elif msg.content_type == "tool_use" and msg.tool_name:
        status.phase = "tool"
        status.tool_name = msg.tool_name
        input_preview = ""
        if msg.tool_input:
            input_preview = json.dumps(msg.tool_input, ensure_ascii=False)[:120]
        log_f.write(f"[tool:{msg.tool_name}] {input_preview}\n")
        log_f.flush()


_last_status_len = 0


def _update_status(status: StatusSnapshot, project_status_path: Path) -> None:
    """Print status line to stderr and write status file."""
    global _last_status_len
    line = format_status_line(status)
    padded = line.ljust(_last_status_len)
    sys.stderr.write(f"\r{padded}")
    sys.stderr.flush()
    _last_status_len = len(line)
    write_status(status, project_status_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Execute a single pipeline node")
    parser.add_argument("sandbox", help="Sandbox directory path")
    parser.add_argument("node_index", type=int, help="Node index (0-based)")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    result = execute_node(args.sandbox, args.node_index)

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"✅ Node '{result['node_id']}' complete ({result['duration_seconds']}s, ${result['cost_usd']:.4f})")
        else:
            print(f"❌ Node '{result['node_id']}' failed (exit {result['exit_code']})")

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
