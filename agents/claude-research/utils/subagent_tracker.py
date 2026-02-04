"""Comprehensive tracking system for subagent tool calls using hooks and message stream."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict

from shared.emitter import emit


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""
    timestamp: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
    subagent_type: str
    parent_tool_use_id: Optional[str] = None
    tool_output: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class SubagentSession:
    """Information about a subagent execution session."""
    subagent_type: str
    parent_tool_use_id: str
    spawned_at: str
    description: str
    prompt_preview: str
    subagent_id: str  # Unique identifier like "RESEARCHER-1"
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


class SubagentTracker:
    """
    Tracks all tool calls made by subagents using both hooks and message stream parsing.

    This tracker:
    1. Monitors the message stream to detect subagent spawns via Task tool
    2. Uses hooks (PreToolUse/PostToolUse) to capture all tool invocations
    3. Associates tool calls with their originating subagent
    4. Emits events for tool usage
    """

    def __init__(self, workspace: Optional[str] = None):
        # Map: parent_tool_use_id -> SubagentSession
        self.sessions: dict[str, SubagentSession] = {}

        # Map: tool_use_id -> ToolCallRecord (for efficient lookup in post hook)
        self.tool_call_records: dict[str, ToolCallRecord] = {}

        # Current execution context (from message stream)
        self._current_parent_id: Optional[str] = None

        # Counter for each subagent type to create unique IDs
        self.subagent_counters: dict[str, int] = defaultdict(int)

        # Tool call detail log (JSONL format)
        self.tool_log_file = None
        if workspace:
            logs_dir = Path(workspace) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tool_log_path = logs_dir / f"tool_calls_{timestamp}.jsonl"
            self.tool_log_file = open(tool_log_path, "w", encoding="utf-8")

    def register_subagent_spawn(
        self,
        tool_use_id: str,
        subagent_type: str,
        description: str,
        prompt: str
    ) -> str:
        """
        Register a new subagent spawn detected from the message stream.

        Args:
            tool_use_id: The ID of the Task tool use block
            subagent_type: Type of subagent (e.g., 'researcher', 'report-writer')
            description: Brief description of the task
            prompt: The full prompt given to the subagent

        Returns:
            The generated subagent_id (e.g., 'RESEARCHER-1')
        """
        # Increment counter for this subagent type and create unique ID
        self.subagent_counters[subagent_type] += 1
        subagent_id = f"{subagent_type.upper()}-{self.subagent_counters[subagent_type]}"

        session = SubagentSession(
            subagent_type=subagent_type,
            parent_tool_use_id=tool_use_id,
            spawned_at=datetime.now().isoformat(),
            description=description,
            prompt_preview=prompt[:200] + "..." if len(prompt) > 200 else prompt,
            subagent_id=subagent_id
        )

        self.sessions[tool_use_id] = session

        # Emit subagent spawn event
        emit("subagent_spawn", {
            "subagent_id": subagent_id,
            "subagent_type": subagent_type,
            "description": description,
        })

        return subagent_id

    def set_current_context(self, parent_tool_use_id: Optional[str]):
        """
        Update the current execution context from message stream.

        Args:
            parent_tool_use_id: The parent tool use ID from the current message
        """
        self._current_parent_id = parent_tool_use_id

    def _log_to_jsonl(self, log_entry: dict[str, Any]):
        """Write structured log entry to JSONL file."""
        if self.tool_log_file:
            self.tool_log_file.write(json.dumps(log_entry) + "\n")
            self.tool_log_file.flush()

    def _format_tool_input(self, tool_input: dict[str, Any], max_length: int = 100) -> str:
        """Format tool input for human-readable logging."""
        if not tool_input:
            return ""

        # WebSearch: show query
        if 'query' in tool_input:
            query = str(tool_input['query'])
            return f"query='{query if len(query) <= max_length else query[:max_length] + '...'}'"

        # Write: show file path and content size
        if 'file_path' in tool_input and 'content' in tool_input:
            filename = Path(tool_input['file_path']).name
            return f"file='{filename}' ({len(tool_input['content'])} chars)"

        # Read/Glob: show path or pattern
        if 'file_path' in tool_input:
            return f"path='{tool_input['file_path']}'"
        if 'pattern' in tool_input:
            return f"pattern='{tool_input['pattern']}'"

        # Task: show subagent spawn
        if 'subagent_type' in tool_input:
            return f"spawn={tool_input.get('subagent_type', '')} ({tool_input.get('description', '')})"

        # Fallback: generic (truncated)
        return str(tool_input)[:max_length]

    async def pre_tool_use_hook(self, hook_input, tool_use_id, context):
        """Hook callback for PreToolUse events - captures tool calls."""
        tool_name = hook_input['tool_name']
        tool_input = hook_input['tool_input']
        timestamp = datetime.now().isoformat()

        # Determine agent context
        is_subagent = self._current_parent_id and self._current_parent_id in self.sessions

        if is_subagent:
            session = self.sessions[self._current_parent_id]
            agent_id = session.subagent_id
            agent_type = session.subagent_type

            # Create and store record for subagent
            record = ToolCallRecord(
                timestamp=timestamp,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id,
                subagent_type=agent_type,
                parent_tool_use_id=self._current_parent_id
            )
            session.tool_calls.append(record)
            self.tool_call_records[tool_use_id] = record

            # Emit tool use event
            emit("tool_use", {
                "id": tool_use_id,
                "name": tool_name,
                "agent_id": agent_id,
                "input": self._format_tool_input(tool_input),
            })

            self._log_to_jsonl({
                "event": "tool_call_start",
                "timestamp": timestamp,
                "tool_use_id": tool_use_id,
                "agent_id": agent_id,
                "agent_type": agent_type,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "parent_tool_use_id": self._current_parent_id
            })
        elif tool_name == "TodoWrite":
            # TodoWrite from lead agent - emit todo_update for DeepAgents-style progress UI
            todos = tool_input.get("todos", [])
            if todos:
                items = [
                    {
                        "content": t.get("content", t.get("activeForm", "")),
                        "status": t.get("status", "pending"),
                    }
                    for t in todos
                ]
                emit("todo_update", {"items": items})
        elif tool_name != "Task":  # Skip Task calls for main agent
            # Main agent tool call
            emit("tool_use", {
                "id": tool_use_id,
                "name": tool_name,
                "agent_id": "LEAD",
                "input": self._format_tool_input(tool_input),
            })

            self._log_to_jsonl({
                "event": "tool_call_start",
                "timestamp": timestamp,
                "tool_use_id": tool_use_id,
                "agent_id": "LEAD",
                "agent_type": "lead",
                "tool_name": tool_name,
                "tool_input": tool_input
            })

        return {'continue_': True}

    async def post_tool_use_hook(self, hook_input, tool_use_id, context):
        """Hook callback for PostToolUse events - captures tool results."""
        tool_response = hook_input.get('tool_response')
        record = self.tool_call_records.get(tool_use_id)

        if not record:
            return {'continue_': True}

        # Update record with output
        record.tool_output = tool_response

        # Check for errors
        error = tool_response.get('error') if isinstance(tool_response, dict) else None
        if error:
            record.error = error

        # Get agent info for logging
        session = self.sessions.get(record.parent_tool_use_id)
        agent_id = session.subagent_id if session else "LEAD"
        agent_type = session.subagent_type if session else "lead"

        # Log completion to JSONL
        self._log_to_jsonl({
            "event": "tool_call_complete",
            "timestamp": datetime.now().isoformat(),
            "tool_use_id": tool_use_id,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "tool_name": record.tool_name,
            "success": error is None,
            "error": error,
            "output_size": len(str(tool_response)) if tool_response else 0
        })

        return {'continue_': True}

    def close(self):
        """Close the tool log file."""
        if self.tool_log_file:
            self.tool_log_file.close()
