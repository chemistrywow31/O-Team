"""O-Team CLI — Stream JSON event parser.

Parses newline-delimited JSON events from `claude -p --output-format stream-json --verbose`.
Ported from O-Team-Web's json-stream-parser.ts to Python.

Event types:
  - system: Lifecycle events (init, task_started, task_progress, task_notification)
  - assistant: Content events (text, tool_use)
  - result: Completion event (success/error, duration, cost)
"""

import json
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StreamMessage:
    """Parsed assistant content event."""
    content_type: str  # "text" or "tool_use"
    text: str | None = None
    tool_name: str | None = None
    tool_input: dict | None = None


@dataclass
class CompleteMessage:
    """Parsed result event."""
    result: str
    duration_ms: float = 0
    cost_usd: float = 0
    is_error: bool = False
    num_turns: int = 0
    session_id: str = ""


@dataclass
class AgentEvent:
    """Parsed agent lifecycle event."""
    kind: str  # "agent_spawn", "agent_progress", "agent_complete"
    task_id: str = ""
    tool_use_id: str = ""
    agent_name: str = ""
    agent_type: str = ""
    description: str = ""
    last_tool: str = ""
    token_count: int | None = None
    status: str = ""


@dataclass
class StatusSnapshot:
    """Current execution status for the status line."""
    run_id: str = ""
    pipeline_name: str = ""
    node_id: str = ""
    node_index: int = 0
    total_nodes: int = 0
    team: str = ""
    phase: str = "idle"  # idle, running, tool, agent, complete, error
    tool_name: str = ""
    agent_name: str = ""
    agent_description: str = ""
    last_text_preview: str = ""
    cost_usd: float = 0
    duration_ms: float = 0
    num_turns: int = 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class StreamParser:
    """Parses stream-json events and tracks agent registry."""

    def __init__(self) -> None:
        # Maps tool_use_id -> agent info for linking
        self._agent_registry: dict[str, dict[str, str]] = {}
        # Maps task_id -> agent info after linking
        self._task_agents: dict[str, dict[str, str]] = {}

    def parse_line(self, line: str) -> StreamMessage | list[StreamMessage] | CompleteMessage | None:
        """Parse a single JSON line into typed event(s).

        Returns StreamMessage, list[StreamMessage], CompleteMessage, or None.
        """
        parsed = _safe_parse(line)
        if parsed is None:
            return None

        event_type = parsed.get("type")

        if event_type == "system":
            return None

        if event_type == "assistant":
            message = parsed.get("message", {})
            content = message.get("content", [])
            if not isinstance(content, list) or len(content) == 0:
                return None

            messages = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    messages.append(StreamMessage(
                        content_type="text",
                        text=item.get("text", ""),
                    ))
                elif item.get("type") == "tool_use":
                    messages.append(StreamMessage(
                        content_type="tool_use",
                        tool_name=item.get("name", ""),
                        tool_input=item.get("input"),
                    ))

            if not messages:
                return None
            if len(messages) == 1:
                return messages[0]
            return messages

        if event_type == "result":
            return CompleteMessage(
                result=parsed.get("result", ""),
                duration_ms=parsed.get("duration_ms", 0),
                cost_usd=parsed.get("cost_usd", 0),
                is_error=parsed.get("is_error", False),
                num_turns=parsed.get("num_turns", 0),
                session_id=parsed.get("session_id", ""),
            )

        return None

    def parse_agent_event(self, line: str) -> AgentEvent | None:
        """Parse a single JSON line for agent lifecycle events.

        Tracks agent spawn/progress/complete through tool_use_id -> task_id linking.
        """
        parsed = _safe_parse(line)
        if parsed is None:
            return None

        event_type = parsed.get("type")

        # Extract agent spawn from assistant tool_use Agent entry
        if event_type == "assistant":
            message = parsed.get("message", {})
            content = message.get("content", [])
            if not isinstance(content, list):
                return None

            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_use" and item.get("name") == "Agent":
                    inp = item.get("input", {})
                    tool_use_id = item.get("id", "")
                    agent_info = {
                        "name": inp.get("name") or inp.get("description", "Agent"),
                        "type": inp.get("subagent_type", "general-purpose"),
                        "description": inp.get("description", ""),
                    }
                    self._agent_registry[tool_use_id] = agent_info
                    return AgentEvent(
                        kind="agent_spawn",
                        tool_use_id=tool_use_id,
                        agent_name=agent_info["name"],
                        agent_type=agent_info["type"],
                        description=agent_info["description"],
                    )
            return None

        if event_type != "system":
            return None

        subtype = parsed.get("subtype", "")

        if subtype == "task_started":
            task_id = parsed.get("task_id", "")
            tool_use_id = parsed.get("tool_use_id", "")
            # Link task_id to previously seen agent info
            if tool_use_id in self._agent_registry:
                self._task_agents[task_id] = self._agent_registry[tool_use_id]
            return AgentEvent(
                kind="agent_spawn",
                task_id=task_id,
                tool_use_id=tool_use_id,
            )

        if subtype == "task_progress":
            task_id = parsed.get("task_id", "")
            token_count = _extract_token_count(parsed.get("usage"))
            agent_info = self._task_agents.get(task_id, {})
            return AgentEvent(
                kind="agent_progress",
                task_id=task_id,
                tool_use_id=parsed.get("tool_use_id", ""),
                agent_name=agent_info.get("name", ""),
                agent_type=agent_info.get("type", ""),
                description=parsed.get("description", ""),
                last_tool=parsed.get("last_tool_name", ""),
                token_count=token_count,
            )

        if subtype == "task_notification":
            task_id = parsed.get("task_id", "")
            agent_info = self._task_agents.get(task_id, {})
            # Clean up registry
            self._task_agents.pop(task_id, None)
            return AgentEvent(
                kind="agent_complete",
                task_id=task_id,
                agent_name=agent_info.get("name", ""),
                agent_type=agent_info.get("type", ""),
                status=parsed.get("status", ""),
                description=parsed.get("summary", ""),
            )

        return None

    def reset(self) -> None:
        """Clear agent registry between nodes."""
        self._agent_registry.clear()
        self._task_agents.clear()


# ---------------------------------------------------------------------------
# Status file writer
# ---------------------------------------------------------------------------

STATUS_FILE_NAME = "status.json"

# Global status path — always at ~/.o-team/status.json so the statusline can find it
_GLOBAL_STATUS_PATH: "Path | None" = None


def _get_global_status_path() -> "Path":
    """Get the global status file path at ~/.o-team/status.json."""
    global _GLOBAL_STATUS_PATH
    if _GLOBAL_STATUS_PATH is None:
        from pathlib import Path
        _GLOBAL_STATUS_PATH = Path.home() / ".o-team" / STATUS_FILE_NAME
    return _GLOBAL_STATUS_PATH


def write_status(status: StatusSnapshot, project_status_path: "Path | None" = None) -> None:
    """Write current status snapshot to JSON file for status line consumption.

    Writes to both:
    - ~/.o-team/status.json (global — for claude-hud --extra-cmd)
    - project_status_path (local — if provided)
    """
    data = {
        "run_id": status.run_id,
        "pipeline": status.pipeline_name,
        "node": status.node_id,
        "progress": f"{status.node_index + 1}/{status.total_nodes}",
        "team": status.team,
        "phase": status.phase,
        "tool": status.tool_name,
        "agent": status.agent_name,
        "agent_desc": status.agent_description,
        "preview": status.last_text_preview[:80] if status.last_text_preview else "",
        "cost": status.cost_usd,
        "duration_ms": status.duration_ms,
        "turns": status.num_turns,
    }

    # Write global status
    global_path = _get_global_status_path()
    global_path.parent.mkdir(parents=True, exist_ok=True)
    with open(global_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # Write project-local status if path provided
    if project_status_path is not None:
        project_status_path.parent.mkdir(parents=True, exist_ok=True)
        with open(project_status_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)


def clear_status(project_status_path: "Path | None" = None) -> None:
    """Remove status files when pipeline completes."""
    try:
        _get_global_status_path().unlink(missing_ok=True)
    except OSError:
        pass
    if project_status_path is not None:
        try:
            project_status_path.unlink(missing_ok=True)
        except OSError:
            pass


def format_status_line(status: StatusSnapshot) -> str:
    """Format a single-line status string for terminal display.

    Examples:
      [2/5] 01-research (research-team) | Read: src/main.py
      [2/5] 01-research (research-team) | Agent: explore-codebase
      [2/5] 01-research (research-team) | Writing...
    """
    progress = f"[{status.node_index + 1}/{status.total_nodes}]"
    node_info = f"{status.node_id} ({status.team})"

    if status.phase == "tool" and status.tool_name:
        detail = f"Tool: {status.tool_name}"
    elif status.phase == "agent" and status.agent_name:
        desc = f" - {status.agent_description}" if status.agent_description else ""
        detail = f"Agent: {status.agent_name}{desc}"
    elif status.phase == "complete":
        cost = f"${status.cost_usd:.4f}" if status.cost_usd else ""
        dur = f"{status.duration_ms / 1000:.1f}s" if status.duration_ms else ""
        parts = [p for p in [dur, cost] if p]
        detail = f"Done ({', '.join(parts)})" if parts else "Done"
    elif status.phase == "error":
        detail = "Error"
    else:
        detail = "Running..."

    return f"{progress} {node_info} | {detail}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_parse(line: str) -> dict[str, Any] | None:
    """Safely parse a JSON line, return None on failure."""
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _extract_token_count(usage: Any) -> int | None:
    """Extract total_tokens from usage field (can be str or dict)."""
    if usage is None:
        return None
    if isinstance(usage, dict):
        tokens = usage.get("total_tokens")
        if isinstance(tokens, (int, float)):
            return int(tokens)
    if isinstance(usage, str):
        import re
        match = re.search(r"total_tokens['\"]?\s*[:'\"]\s*['\"]?\s*(\d+)", usage)
        if match:
            return int(match.group(1))
    return None


def is_complete(msg: Any) -> bool:
    """Check if a parsed message is a CompleteMessage."""
    return isinstance(msg, CompleteMessage)
