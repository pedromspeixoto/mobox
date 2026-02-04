"""
Centralized event emission for streaming to frontend.

This does not replace sending custom agent events, just supports sending additional ones.
"""


import json
from typing import Any


def emit(event_type: str, data: dict[str, Any]) -> None:
    """Emit a JSON event to stdout for streaming to frontend.

    Args:
        event_type: The type of event (e.g., "status", "text", "error")
        data: Dictionary of event data
    """
    print(json.dumps({"type": event_type, "data": data}), flush=True)


def emit_status(message: str) -> None:
    """Emit a status update event.

    Args:
        message: Status message to display
    """
    emit("status", {"message": message})


def emit_text(content: str) -> None:
    """Emit text content to display to the user.

    Args:
        content: Text content to display
    """
    emit("text", {"content": content})


def emit_error(message: str) -> None:
    """Emit an error event.

    Args:
        message: Error message
    """
    emit("error", {"message": message})


def emit_warning(message: str) -> None:
    """Emit a warning event.

    Args:
        message: Warning message
    """
    emit("warning", {"message": message})


def emit_thinking(content: str) -> None:
    """Emit a thinking/reasoning event.

    Args:
        content: The thinking content
    """
    emit("thinking", {"content": content})


def emit_think(thought: str) -> None:
    """Emit a think event for agent reflection/reasoning.
    
    Use this in think tools to surface the agent's reasoning process to users.
    Renders as a "Thought for Xs" collapsible block in the frontend.

    Args:
        thought: The agent's reflection - what was found, gaps, next steps
    """
    import uuid
    emit("think", {"id": f"think_{uuid.uuid4().hex[:8]}", "thought": thought})


def emit_tool_use(tool_id: str, name: str, tool_input: dict[str, Any]) -> None:
    """Emit a tool use event.

    Args:
        tool_id: Unique identifier for the tool use
        name: Name of the tool being used
        tool_input: Input parameters for the tool
    """
    emit("tool_use", {"id": tool_id, "name": name, "input": tool_input})


def emit_result(
    session_id: str,
    duration_ms: int,
    num_turns: int,
    is_error: bool = False,
    total_cost_usd: float | None = None,
) -> None:
    """Emit a result event with session statistics.

    Args:
        session_id: The session identifier
        duration_ms: Total duration in milliseconds
        num_turns: Number of conversation turns
        is_error: Whether the session ended in error
        total_cost_usd: Optional total cost in USD
    """
    emit("result", {
        "session_id": session_id,
        "duration_ms": duration_ms,
        "num_turns": num_turns,
        "is_error": is_error,
        "total_cost_usd": total_cost_usd,
    })


def emit_subagent_start(agent_name: str, task: str) -> None:
    """Emit event when starting a subagent.

    Args:
        agent_name: Name of the subagent (e.g., "researcher", "data_analyst")
        task: Brief description of the task
    """
    emit("subagent_start", {"agent": agent_name, "task": task})


def emit_subagent_complete(agent_name: str, summary: str) -> None:
    """Emit event when a subagent completes.

    Args:
        agent_name: Name of the subagent
        summary: Brief summary of what was accomplished
    """
    emit("subagent_complete", {"agent": agent_name, "summary": summary})


def emit_todo_create(items: list[dict[str, Any]]) -> None:
    """Emit event when a new todo list is created.

    Args:
        items: List of todo items, each with 'content', 'status' (pending/in_progress/completed)
    """
    emit("todo_create", {"items": items})


def emit_todo_update(items: list[dict[str, Any]]) -> None:
    """Emit event when the todo list is updated.

    Args:
        items: Updated list of todo items
    """
    emit("todo_update", {"items": items})


def emit_todo_done(item: dict[str, Any], index: int) -> None:
    """Emit event when a todo item is completed.

    Args:
        item: The completed todo item
        index: Index of the completed item in the list
    """
    emit("todo_done", {"item": item, "index": index})


def emit_done() -> None:
    """Emit a done event to signal completion."""
    emit("done", {})
