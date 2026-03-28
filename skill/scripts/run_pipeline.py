"""O-Team CLI — Pipeline execution engine.

Usage:
    python -m scripts.run_pipeline <pipeline-yaml>
        [--input <text-or-file-path>]
        [--json]

    python -m scripts.run_pipeline --resume <run-id>
        [--project-dir <path>]
        [--json]

Creates a UUID sandbox, copies team configurations into office folders,
assembles prompts, and sequentially spawns independent claude CLI processes.
Each node runs in its own context with its own team identity.
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import utils
from .prompt import assemble_prompt
from .stream_parser import (
    StreamParser,
    StatusSnapshot,
    CompleteMessage,
    StreamMessage,
    format_status_line,
    is_complete,
    process_stream_message,
    write_status,
    clear_status,
    STATUS_FILE_NAME,
)
from .validate_pipeline import validate_pipeline


# ---------------------------------------------------------------------------
# Sandbox setup
# ---------------------------------------------------------------------------


def _create_sandbox(pipeline: dict, project_dir: Path) -> dict:
    """Create a UUID-isolated sandbox for this run.

    Returns the run state dict.
    """
    run_id = utils.generate_run_id()
    runs_dir = project_dir / utils.RUNS_DIR_NAME
    sandbox = runs_dir / run_id

    # Create sandbox structure
    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / "workspace").mkdir(exist_ok=True)

    # Create office folders and copy team configs
    nodes_state = []
    for node in pipeline["nodes"]:
        office = sandbox / node["id"]
        office.mkdir(exist_ok=True)

        # Copy team configuration into office folder
        team_path = Path(node["team_path"])
        utils.copy_team_config(team_path, office)

        nodes_state.append({
            "id": node["id"],
            "team": node["team"],
            "team_path": node["team_path"],
            "mode": node["mode"],
            "prompt": node["prompt"],
            "timeout": node.get("timeout", utils.DEFAULT_TIMEOUT),
            "state": "PENDING",
            "exit_code": None,
            "error": None,
            "started_at": None,
            "finished_at": None,
        })

    # Save pipeline snapshot
    utils.write_yaml(sandbox / "snapshot.yaml", pipeline)

    # Build run state
    run_state = {
        "run_id": run_id,
        "pipeline_name": pipeline.get("name", ""),
        "pipeline_slug": pipeline.get("slug", ""),
        "state": "PENDING",
        "nodes": nodes_state,
        "current_node_index": 0,
        "sandbox_path": str(sandbox),
        "created_at": utils.now_iso(),
        "started_at": None,
        "finished_at": None,
    }

    utils.write_json(sandbox / "meta.json", run_state)
    return run_state


# ---------------------------------------------------------------------------
# Node execution
# ---------------------------------------------------------------------------


def _execute_node(
    node: dict,
    sandbox: Path,
    prompt_content: str,
    run_state: dict,
    status_path: Path,
) -> int:
    """Execute a single pipeline node by spawning a claude CLI process.

    Uses --output-format stream-json to receive structured events.
    Parses events to update the status line and log file.

    Returns the exit code of the process.
    """
    office = sandbox / node["id"]

    # Write prompt.md for audit trail
    prompt_file = office / "prompt.md"
    utils.write_text(prompt_file, prompt_content)

    # Build command with stream-json output
    cmd = [
        "claude",
        "-p", prompt_content,
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
    ]

    # File paths
    log_file = office / "run.log"
    events_file = office / "events.jsonl"

    # Status tracking
    parser = StreamParser()
    status = StatusSnapshot(
        run_id=run_state["run_id"],
        pipeline_name=run_state.get("pipeline_name", ""),
        node_id=node["id"],
        node_index=run_state["current_node_index"],
        total_nodes=len(run_state["nodes"]),
        team=node["team"],
        phase="running",
    )
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
                bufsize=1,  # Line buffered
            )

            for line in process.stdout:
                # Archive raw event
                evt_f.write(line)
                evt_f.flush()

                # Parse display events
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
                    # Log final result
                    log_f.write(f"\n--- result ---\n{cm.result}\n")
                    log_f.flush()
                    # Print status
                    _print_status(status)
                    write_status(status, status_path)

                elif isinstance(msg, list):
                    for m in msg:
                        process_stream_message(m, status, log_f)
                    _print_status(status)
                    write_status(status, status_path)

                elif isinstance(msg, StreamMessage):
                    process_stream_message(msg, status, log_f)
                    _print_status(status)
                    write_status(status, status_path)

                # Parse agent events (separate track)
                agent_evt = parser.parse_agent_event(line)
                if agent_evt is not None:
                    if agent_evt.kind == "agent_spawn" and agent_evt.agent_name:
                        status.phase = "agent"
                        status.agent_name = agent_evt.agent_name
                        status.agent_description = agent_evt.description
                        log_f.write(f"[agent:spawn] {agent_evt.agent_name} ({agent_evt.agent_type})\n")
                        log_f.flush()
                        _print_status(status)
                        write_status(status, status_path)
                    elif agent_evt.kind == "agent_progress":
                        if agent_evt.last_tool:
                            status.tool_name = agent_evt.last_tool
                        if agent_evt.description:
                            status.agent_description = agent_evt.description
                        log_f.write(f"[agent:progress] {agent_evt.agent_name or agent_evt.task_id} tool={agent_evt.last_tool}\n")
                        log_f.flush()
                        _print_status(status)
                        write_status(status, status_path)
                    elif agent_evt.kind == "agent_complete":
                        status.phase = "running"
                        status.agent_name = ""
                        status.agent_description = ""
                        log_f.write(f"[agent:complete] {agent_evt.agent_name or agent_evt.task_id} status={agent_evt.status}\n")
                        log_f.flush()
                        _print_status(status)
                        write_status(status, status_path)

            process.wait()
            parser.reset()
            return process.returncode

    except FileNotFoundError:
        error_msg = "ERROR: 'claude' command not found. Ensure Claude Code CLI is installed.\n"
        sys.stderr.write(error_msg)
        with open(log_file, "a", encoding="utf-8") as log_f:
            log_f.write(error_msg)
        return 127

    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130


# Last printed status line length (for clearing)
_last_status_len = 0


def _print_status(status: StatusSnapshot) -> None:
    """Print current status to stderr as a single overwriting line."""
    global _last_status_len
    line = format_status_line(status)
    # Overwrite previous status line using \r
    padded = line.ljust(_last_status_len)
    sys.stderr.write(f"\r{padded}")
    sys.stderr.flush()
    _last_status_len = len(line)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def run_pipeline(
    pipeline_path_str: str | None = None,
    input_content: str | None = None,
    resume_run_id: str | None = None,
    project_dir: Path | None = None,
) -> dict:
    """Run a pipeline from start or resume from a paused state.

    Args:
        pipeline_path_str: Path to pipeline YAML (for new runs)
        input_content: Initial input text or file path (for new runs)
        resume_run_id: Run ID to resume (for --resume)
        project_dir: Project directory (default: cwd)

    Returns:
        dict with run result
    """
    proj_dir = utils.ensure_project_dir(project_dir)

    if resume_run_id:
        return _resume_run(resume_run_id, proj_dir)
    else:
        return _start_new_run(pipeline_path_str, input_content, proj_dir)


def _start_new_run(
    pipeline_path_str: str,
    input_content: str | None,
    project_dir: Path,
) -> dict:
    """Start a new pipeline run."""
    # Validate pipeline
    validation = validate_pipeline(pipeline_path_str)
    if not validation["valid"]:
        return {
            "success": False,
            "error": "Pipeline 驗證失敗",
            "validation": validation,
        }

    pipeline = validation["pipeline"]

    # Create sandbox
    run_state = _create_sandbox(pipeline, project_dir)
    sandbox = Path(run_state["sandbox_path"])

    # Write initial input
    if input_content:
        first_node_id = run_state["nodes"][0]["id"]
        input_path = sandbox / first_node_id / "input.md"

        # Check if input_content is a file path
        potential_file = Path(input_content)
        if potential_file.exists() and potential_file.is_file():
            shutil.copy2(potential_file, input_path)
        else:
            utils.write_text(input_path, input_content)

    # Start execution
    return _execute_pipeline(run_state, sandbox)


def _resume_run(run_id: str, project_dir: Path) -> dict:
    """Resume a paused or errored run."""
    runs_dir = project_dir / utils.RUNS_DIR_NAME
    sandbox = runs_dir / run_id

    if not sandbox.exists():
        return {
            "success": False,
            "error": f"Run '{run_id}' not found at {sandbox}",
        }

    meta_file = sandbox / "meta.json"
    if not meta_file.exists():
        return {
            "success": False,
            "error": f"Run '{run_id}' has no meta.json",
        }

    run_state = utils.read_json(meta_file)

    if run_state["state"] not in ("PAUSED", "ERROR"):
        return {
            "success": False,
            "error": f"Run '{run_id}' is in state '{run_state['state']}', cannot resume (must be PAUSED or ERROR)",
        }

    return _execute_pipeline(run_state, sandbox)


def _execute_pipeline(run_state: dict, sandbox: Path) -> dict:
    """Execute pipeline nodes sequentially from current position."""
    run_state["state"] = "RUNNING"
    run_state["started_at"] = run_state.get("started_at") or utils.now_iso()
    _save_state(run_state, sandbox)

    nodes = run_state["nodes"]
    total = len(nodes)

    # Project-local status file (in .o-team/ directory)
    project_status_path = sandbox.parent.parent / STATUS_FILE_NAME

    for i in range(run_state["current_node_index"], total):
        node = nodes[i]
        run_state["current_node_index"] = i

        # Skip already completed or skipped nodes
        if node["state"] in ("COMPLETE", "SKIPPED"):
            continue

        # Print node header
        print(f"\n{'='*60}")
        print(f"▶ Node {i+1}/{total}: {node['id']}")
        print(f"  Team: {node['team']}")
        mode_label = "auto ⚡" if node["mode"] == "auto" else "gate ⏸"
        print(f"  Mode: {mode_label}")
        print(f"{'='*60}\n")

        # Assemble prompt
        is_first = (i == 0)
        prompt_content = assemble_prompt(node, sandbox, is_first)

        # Execute
        node["state"] = "RUNNING"
        node["started_at"] = utils.now_iso()
        _save_state(run_state, sandbox)

        start_time = time.time()
        exit_code = _execute_node(node, sandbox, prompt_content, run_state, project_status_path)
        elapsed = time.time() - start_time

        # Clear the status line after node completes
        sys.stderr.write("\r" + " " * 120 + "\r")
        sys.stderr.flush()

        node["exit_code"] = exit_code
        node["finished_at"] = utils.now_iso()

        if exit_code != 0:
            node["state"] = "ERROR"
            node["error"] = f"Exit code: {exit_code}"
            run_state["state"] = "ERROR"
            _save_state(run_state, sandbox)

            print(f"\n❌ Node '{node['id']}' failed (exit {exit_code}, {elapsed:.1f}s)")
            print(f"   Run ID: {run_state['run_id']}")
            print(f"   操作: python -m scripts.approve_node {run_state['run_id']} {node['id']} retry|skip|abort")

            clear_status(project_status_path)
            return {
                "success": False,
                "run_id": run_state["run_id"],
                "state": "ERROR",
                "failed_node": node["id"],
                "exit_code": exit_code,
            }

        # Node succeeded
        print(f"\n✅ Node '{node['id']}' complete ({elapsed:.1f}s)")

        if node["mode"] == "auto":
            node["state"] = "COMPLETE"
            _save_state(run_state, sandbox)

            # Transfer output to next node's input
            if i + 1 < total:
                _transfer_output(node, nodes[i + 1], sandbox)
                print(f"   → auto-proceeding to {nodes[i+1]['id']}")

        elif node["mode"] == "gate":
            node["state"] = "PAUSED_FOR_REVIEW"
            run_state["state"] = "PAUSED"
            _save_state(run_state, sandbox)

            # Show output preview
            _print_output_preview(node, sandbox)

            print(f"\n⏸  Waiting for review")
            print(f"   Run ID: {run_state['run_id']}")
            print(f"   操作:")
            print(f"     approve: python -m scripts.approve_node {run_state['run_id']} {node['id']} approve")
            print(f"     reject:  python -m scripts.approve_node {run_state['run_id']} {node['id']} reject")
            print(f"     abort:   python -m scripts.approve_node {run_state['run_id']} {node['id']} abort")

            clear_status(project_status_path)
            return {
                "success": True,
                "run_id": run_state["run_id"],
                "state": "PAUSED",
                "paused_node": node["id"],
                "node_index": i,
                "remaining": total - i - 1,
            }

    # All nodes complete
    run_state["state"] = "COMPLETE"
    run_state["finished_at"] = utils.now_iso()
    _save_state(run_state, sandbox)

    clear_status(project_status_path)
    print(f"\n🏁 Pipeline '{run_state['pipeline_name']}' complete")
    print(f"   Run ID: {run_state['run_id']}")
    print(f"   最終產出: {sandbox / nodes[-1]['id'] / 'output.md'}")

    return {
        "success": True,
        "run_id": run_state["run_id"],
        "state": "COMPLETE",
        "output_path": str(sandbox / nodes[-1]["id"] / "output.md"),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_state(run_state: dict, sandbox: Path) -> None:
    """Save run state to meta.json."""
    utils.write_json(sandbox / "meta.json", run_state)


def _transfer_output(from_node: dict, to_node: dict, sandbox: Path) -> None:
    """Copy output.md from completed node to next node's input.md."""
    src = sandbox / from_node["id"] / "output.md"
    dst = sandbox / to_node["id"] / "input.md"

    if src.exists():
        shutil.copy2(src, dst)
    else:
        # No output.md — create empty input for next node
        utils.write_text(dst, "")


def _print_output_preview(node: dict, sandbox: Path, max_lines: int = 20) -> None:
    """Print a preview of the node's output.md."""
    output_file = sandbox / node["id"] / "output.md"
    if not output_file.exists():
        print("   (無 output.md)")
        return

    content = utils.read_text(output_file)
    lines = content.splitlines()
    preview = lines[:max_lines]

    print(f"\n   ── output.md preview ({len(lines)} lines) ──")
    for line in preview:
        print(f"   │ {line}")
    if len(lines) > max_lines:
        print(f"   │ ... ({len(lines) - max_lines} more lines)")
    print(f"   └──────────────────────────────────")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Run a pipeline")
    parser.add_argument("pipeline", nargs="?", help="Path to pipeline YAML")
    parser.add_argument("--input", default=None,
                        help="Initial input (text or file path)")
    parser.add_argument("--resume", default=None,
                        help="Resume a paused/errored run by ID")
    parser.add_argument("--project-dir", default=None,
                        help="Project directory (default: cwd)")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    if not args.pipeline and not args.resume:
        parser.error("Must provide either a pipeline YAML path or --resume <run-id>")

    proj_dir = Path(args.project_dir) if args.project_dir else None

    result = run_pipeline(
        pipeline_path_str=args.pipeline,
        input_content=args.input,
        resume_run_id=args.resume,
        project_dir=proj_dir,
    )

    if args.json:
        utils.print_json(result)

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
