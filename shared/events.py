"""
Normalized event types and parsers for agent streaming.

Parses raw agent events (from stdout JSON) into a unified StreamEvent format.
Used by the API before converting to AI SDK SSE.

Usage:
    from shared.events import get_parser, EventType, StreamEvent

    parser = get_parser("claude")
    for raw in agent_events:
        event = parser.parse({"type": raw.type, "data": raw.data})
        # Use event.type, event.data
    content = parser.get_text()
    thinking = parser.get_thinking()
"""

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Normalized event types."""

    START = "start"
    DONE = "done"
    ERROR = "error"
    PING = "ping"
    STATUS = "status"
    TEXT = "text"
    TEXT_DELTA = "text_delta"
    THINKING = "thinking"
    THINKING_DELTA = "thinking_delta"
    TOOL_USE_START = "tool_use_start"
    TOOL_USE_DELTA = "tool_use_delta"
    TOOL_USE_END = "tool_use_end"
    TOOL_RESULT = "tool_result"
    METADATA = "metadata"
    USAGE = "usage"
    RESULT = "result"
    TODO_CREATE = "todo_create"
    TODO_UPDATE = "todo_update"
    TODO_DONE = "todo_done"
    RAW = "raw"
    UNKNOWN = "unknown"


@dataclass
class StreamEvent:
    """Normalized event structure."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    index: int | None = None
    id: str | None = None


class EventParser:
    """
    Parses raw agent events into normalized StreamEvent format.
    Framework-specific; accumulates text/thinking for persistence.
    """

    def __init__(self, framework: str):
        self.framework = framework
        self._accumulated_text: list[str] = []
        self._accumulated_thinking: list[str] = []
        self._sdk_session_id: str | None = None
        # Claude API format state
        self._text_ids: dict[int, str] = {}
        self._thinking_ids: dict[int, str] = {}
        self._tool_ids: dict[int, str] = {}
        self._active_text: set[int] = set()
        self._active_thinking: set[int] = set()

    def parse(self, raw_event: dict[str, Any]) -> StreamEvent:
        """Parse raw event to normalized StreamEvent."""
        if self.framework == "claude":
            return self._parse_claude(raw_event)
        if self.framework in ("deepagents", "langchain"):
            return self._parse_deepagents(raw_event)
        return StreamEvent(type=EventType.UNKNOWN, data=raw_event)

    def _parse_claude(self, raw_event: dict[str, Any]) -> StreamEvent:
        event_type = raw_event.get("type", "unknown")
        data = raw_event.get("data", {})

        # Claude API streaming format
        if event_type == "message_start":
            message = raw_event.get("message", {})
            if message.get("id"):
                self._sdk_session_id = message.get("id")
            return StreamEvent(
                type=EventType.START,
                data={"model": message.get("model"), "usage": message.get("usage", {})},
            )

        if event_type == "content_block_start":
            index = raw_event.get("index", 0)
            block = raw_event.get("content_block", {})
            block_type = block.get("type")

            if block_type == "text":
                self._text_ids[index] = f"text_{uuid.uuid4().hex[:8]}"
                self._active_text.add(index)
                return StreamEvent(type=EventType.TEXT, index=index, id=self._text_ids[index])

            if block_type == "tool_use":
                tool_id = block.get("id", f"call_{uuid.uuid4().hex[:8]}")
                self._tool_ids[index] = tool_id
                return StreamEvent(
                    type=EventType.TOOL_USE_START,
                    data={"id": tool_id, "name": block.get("name"), "input": block.get("input", {})},
                    index=index,
                    id=tool_id,
                )

            if block_type == "thinking":
                self._thinking_ids[index] = f"thinking_{uuid.uuid4().hex[:8]}"
                self._active_thinking.add(index)
                return StreamEvent(type=EventType.THINKING, index=index, id=self._thinking_ids[index])

        if event_type == "content_block_delta":
            index = raw_event.get("index", 0)
            delta = raw_event.get("delta", {})
            delta_type = delta.get("type")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                self._accumulated_text.append(text)
                return StreamEvent(
                    type=EventType.TEXT_DELTA,
                    data={"delta": text},
                    index=index,
                    id=self._text_ids.get(index),
                )

            if delta_type == "thinking_delta":
                thinking = delta.get("thinking", "")
                self._accumulated_thinking.append(thinking)
                return StreamEvent(
                    type=EventType.THINKING_DELTA,
                    data={"delta": thinking},
                    index=index,
                    id=self._thinking_ids.get(index),
                )

            if delta_type == "input_json_delta":
                return StreamEvent(
                    type=EventType.TOOL_USE_DELTA,
                    data={"partial_json": delta.get("partial_json", "")},
                    index=index,
                    id=self._tool_ids.get(index),
                )

        if event_type == "content_block_stop":
            index = raw_event.get("index", 0)
            self._active_text.discard(index)
            self._active_thinking.discard(index)
            if index in self._tool_ids:
                return StreamEvent(type=EventType.TOOL_USE_END, data={"id": self._tool_ids[index]}, index=index)
            return StreamEvent(type=EventType.UNKNOWN, index=index)

        if event_type == "message_delta":
            usage = raw_event.get("usage", {})
            delta = raw_event.get("delta", {})
            return StreamEvent(
                type=EventType.USAGE,
                data={"usage": usage, "stop_reason": delta.get("stop_reason")},
            )

        if event_type == "message_stop":
            return StreamEvent(type=EventType.DONE)

        if event_type == "ping":
            return StreamEvent(type=EventType.PING)

        if event_type == "error":
            error = raw_event.get("error", raw_event.get("data", {}))
            message = error.get("message") or "An error occurred"
            return StreamEvent(type=EventType.ERROR, data={"message": message})

        # Simplified Claude Agent SDK format
        if event_type == "start":
            return StreamEvent(type=EventType.START, data=raw_event.get("data", {}))

        if event_type == "status":
            message = data.get("message", "")
            return StreamEvent(type=EventType.STATUS, data={"message": message})

        if event_type == "text":
            content = data.get("content", "")
            self._accumulated_text.append(content)
            return StreamEvent(type=EventType.TEXT_DELTA, data={"delta": content, "content": content})

        if event_type == "thinking":
            content = data.get("content", "")
            content = content if content.endswith("\n") else content + "\n"
            self._accumulated_thinking.append(content)
            return StreamEvent(type=EventType.THINKING, data={"content": content})

        if event_type == "think":
            thought = data.get("thought", "")
            thought = thought if thought.endswith("\n") else thought + "\n"
            self._accumulated_thinking.append(thought)
            return StreamEvent(type=EventType.THINKING, data={"content": thought, "source": "think_tool"})

        if event_type == "tool_use":
            if data.get("name") == "TodoWrite":
                tool_input = data.get("input", {})
                if isinstance(tool_input, dict):
                    todos = tool_input.get("todos", [])
                else:
                    todos = []
                if todos:
                    items = [
                        {"content": t.get("content", t.get("activeForm", "")), "status": t.get("status", "pending")}
                        for t in todos
                    ]
                    return StreamEvent(type=EventType.TODO_UPDATE, data={"items": items})
            return StreamEvent(type=EventType.TOOL_USE_START, data=data, id=data.get("id"))

        if event_type == "tool_result":
            return StreamEvent(type=EventType.TOOL_RESULT, data=data, id=data.get("tool_use_id"))

        if event_type == "result":
            for key in ("session_id", "sessionId"):
                if key in data and data[key]:
                    self._sdk_session_id = str(data[key])
                    break
            return StreamEvent(type=EventType.RESULT, data=data)

        if event_type == "usage":
            return StreamEvent(type=EventType.USAGE, data={"usage": data})

        if event_type == "usage_total":
            return StreamEvent(type=EventType.USAGE, data={"usage": data, "total": True})

        if event_type in ("todos", "todo_create"):
            items = data.get("items", [])
            return StreamEvent(type=EventType.TODO_CREATE, data={"items": items})

        if event_type == "todo_update":
            items = data.get("items", [])
            return StreamEvent(type=EventType.TODO_UPDATE, data={"items": items})

        if event_type == "todo_done":
            item = data.get("item", {})
            index = data.get("index", 0)
            return StreamEvent(type=EventType.TODO_DONE, data={"item": item, "index": index})

        if event_type == "subagent_spawn":
            subagent_type = data.get("subagent_type", "subagent")
            description = data.get("description", "")
            message = f"Spawning {subagent_type}: {description}" if description else f"Spawning {subagent_type}..."
            return StreamEvent(type=EventType.STATUS, data={"message": message})

        if event_type == "done":
            return StreamEvent(type=EventType.DONE)

        return StreamEvent(type=EventType.UNKNOWN, data=raw_event)

    def _parse_deepagents(self, raw_event: dict[str, Any]) -> StreamEvent:
        event_type = raw_event.get("type", "unknown")
        data = raw_event.get("data", {})

        if event_type == "start":
            return StreamEvent(type=EventType.START, data=data)

        if event_type == "status":
            return StreamEvent(type=EventType.STATUS, data={"message": data.get("message", "")})

        if event_type == "text":
            content = data.get("content", "")
            self._accumulated_text.append(content)
            return StreamEvent(type=EventType.TEXT_DELTA, data={"delta": content})

        if event_type == "thinking":
            content = data.get("content", "")
            content = content if content.endswith("\n") else content + "\n"
            self._accumulated_thinking.append(content)
            return StreamEvent(type=EventType.THINKING, data={"content": content})

        if event_type == "think":
            thought = data.get("thought", "")
            thought = thought if thought.endswith("\n") else thought + "\n"
            self._accumulated_thinking.append(thought)
            return StreamEvent(type=EventType.THINKING, data={"content": thought, "source": "think_tool"})

        if event_type == "tool_use":
            return StreamEvent(type=EventType.TOOL_USE_START, data=data, id=data.get("id"))

        if event_type == "tool_call_start":
            return StreamEvent(
                type=EventType.TOOL_USE_START,
                data={"id": data.get("id", ""), "name": data.get("name", "")},
                id=data.get("id"),
            )

        if event_type == "search":
            return StreamEvent(
                type=EventType.TOOL_USE_START,
                data={
                    "id": data.get("id", f"search_{uuid.uuid4().hex[:8]}"),
                    "name": "internet_search",
                    "input": {"query": data.get("query", ""), "topic": data.get("topic", "general")},
                },
                id=data.get("id"),
            )

        if event_type == "search_result":
            return StreamEvent(
                type=EventType.TOOL_RESULT,
                data={"count": data.get("count", 0), "results": data.get("results", [])},
            )

        if event_type == "tool_result":
            return StreamEvent(type=EventType.TOOL_RESULT, data=data, id=data.get("tool_use_id"))

        if event_type in ("todos", "todo_create"):
            items = data.get("items", [])
            return StreamEvent(type=EventType.TODO_CREATE, data={"items": items})

        if event_type == "todo_update":
            items = data.get("items", [])
            return StreamEvent(type=EventType.TODO_UPDATE, data={"items": items})

        if event_type == "todo_done":
            item = data.get("item", {})
            index = data.get("index", 0)
            return StreamEvent(type=EventType.TODO_DONE, data={"item": item, "index": index})

        if event_type == "subagent_start":
            agent = data.get("agent", "unknown")
            task = data.get("task", "")
            content = f"Starting {agent}: {task}\n"
            self._accumulated_thinking.append(content)
            return StreamEvent(type=EventType.THINKING, data={"content": content, "subagent": agent})

        if event_type == "subagent_complete":
            agent = data.get("agent", "unknown")
            content = f"{agent} completed.\n"
            self._accumulated_thinking.append(content)
            return StreamEvent(type=EventType.THINKING, data={"content": content, "subagent": agent})

        if event_type == "usage":
            return StreamEvent(type=EventType.USAGE, data={"usage": data})

        if event_type == "usage_total":
            return StreamEvent(type=EventType.USAGE, data={"usage": data, "total": True})

        if event_type == "result":
            for key in ("session_id", "sessionId"):
                if key in data and data[key]:
                    self._sdk_session_id = str(data[key])
                    break
            return StreamEvent(type=EventType.RESULT, data=data)

        if event_type == "error":
            message = data.get("message", "An error occurred")
            return StreamEvent(type=EventType.ERROR, data={"message": message})

        if event_type == "done":
            return StreamEvent(type=EventType.DONE)

        return StreamEvent(type=EventType.RAW, data=raw_event)

    def get_text(self) -> str:
        """Accumulated text content for persistence."""
        return "".join(self._accumulated_text)

    def get_thinking(self) -> str:
        """Accumulated thinking content for persistence."""
        return "".join(self._accumulated_thinking)

    def get_sdk_session_id(self) -> str | None:
        """SDK session ID from result event."""
        return self._sdk_session_id


def get_parser(framework: str) -> EventParser:
    """Get parser for the given framework."""
    return EventParser(framework)
