"""
Reusable event parser for Claude Agent SDK streams.

Converts Claude SDK messages (AssistantMessage, ResultMessage) into
normalized events: text, tool_use, todo_create/todo_update, result, etc.

- TodoWrite tool use → todo_update (for DeepAgents-style progress UI)
- Task tool use → on_task callback (for subagent tracking)

Usage:
    from shared.emitter import emit
    from shared.utils.claude_parser import process_assistant_message, process_result_message

    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            process_assistant_message(msg, emit, on_task=tracker.register_subagent_spawn)
        elif isinstance(msg, ResultMessage):
            process_result_message(msg, emit)
"""

from typing import Any, Callable

EmitFn = Callable[[str, dict[str, Any]], None]


def process_assistant_message(
    msg: Any,
    emit: EmitFn,
    *,
    on_task: Callable[[str, str, str, str], str] | None = None,
) -> None:
    """Process an AssistantMessage and emit normalized events.

    Args:
        msg: AssistantMessage from Claude SDK (has .content, .parent_tool_use_id)
        emit: Emit function (type, data) -> None
        on_task: Optional callback when Task tool is used: (tool_use_id, subagent_type, description, prompt) -> subagent_id
    """
    for block in getattr(msg, "content", []) or []:
        block_type = type(block).__name__

        if block_type == "TextBlock":
            text = getattr(block, "text", "") or ""
            if text:
                emit("text", {"content": text})

        elif block_type == "ToolUseBlock":
            tool_id = getattr(block, "id", "")
            tool_name = getattr(block, "name", "")
            tool_input = getattr(block, "input", {}) or {}

            if tool_name == "Task" and on_task:
                subagent_type = tool_input.get("subagent_type", "unknown")
                description = tool_input.get("description", "no description")
                prompt = tool_input.get("prompt", "")
                on_task(tool_id, subagent_type, description, prompt)
            elif tool_name == "TodoWrite":
                # Claude SDK TodoWrite tool - map to todo_create/todo_update
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
            else:
                emit("tool_use", {"id": tool_id, "name": tool_name, "input": tool_input})


def process_result_message(msg: Any, emit: EmitFn) -> None:
    """Process a ResultMessage and emit result event.

    Args:
        msg: ResultMessage from Claude SDK
        emit: Emit function (type, data) -> None
    """
    result_data = {
        "session_id": getattr(msg, "session_id", ""),
        "duration_ms": getattr(msg, "duration_ms", 0),
        "num_turns": getattr(msg, "num_turns", 0),
        "is_error": getattr(msg, "is_error", False),
        "total_cost_usd": getattr(msg, "total_cost_usd", None),
    }
    if getattr(msg, "usage", None):
        result_data["usage"] = msg.usage
    emit("result", result_data)
