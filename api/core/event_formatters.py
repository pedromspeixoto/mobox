"""Event formatters: Convert normalized events to AI SDK SSE format.

Parsing (raw agent events → normalized StreamEvent) is done in shared.events.
This module only converts normalized StreamEvent → AI SDK stream protocol.

Reference: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
"""
import json
import uuid
from typing import Any, Dict

from shared.events import EventType, StreamEvent


class SSEFormatter:
    """Formatter for stream protocol events in SSE format."""

    @staticmethod
    def format(event_data: Dict[str, Any]) -> str:
        data_json = json.dumps(event_data, ensure_ascii=False)
        return f"data: {data_json}\n\n"

    @staticmethod
    def format_done() -> str:
        return "data: [DONE]\n\n"

    @staticmethod
    def format_start(message_id: str) -> str:
        return SSEFormatter.format({"type": "start", "messageId": message_id})

    @staticmethod
    def format_text_start(text_id: str) -> str:
        return SSEFormatter.format({"type": "text-start", "id": text_id})

    @staticmethod
    def format_text_delta(text_id: str, delta: str) -> str:
        return SSEFormatter.format({"type": "text-delta", "id": text_id, "delta": delta})

    @staticmethod
    def format_text_end(text_id: str) -> str:
        return SSEFormatter.format({"type": "text-end", "id": text_id})

    @staticmethod
    def format_reasoning_start(reasoning_id: str, variant: str = "thinking") -> str:
        return SSEFormatter.format({
            "type": "reasoning-start",
            "id": reasoning_id,
            "providerMetadata": {"mobox": {"variant": variant}},
        })

    @staticmethod
    def format_reasoning_delta(reasoning_id: str, delta: str) -> str:
        return SSEFormatter.format({"type": "reasoning-delta", "id": reasoning_id, "delta": delta})

    @staticmethod
    def format_reasoning_end(reasoning_id: str) -> str:
        return SSEFormatter.format({"type": "reasoning-end", "id": reasoning_id})

    @staticmethod
    def format_tool_input_start(tool_call_id: str, tool_name: str) -> str:
        return SSEFormatter.format({
            "type": "tool-input-start",
            "toolCallId": tool_call_id,
            "toolName": tool_name,
        })

    @staticmethod
    def format_tool_input_delta(tool_call_id: str, input_text_delta: str) -> str:
        return SSEFormatter.format({
            "type": "tool-input-delta",
            "toolCallId": tool_call_id,
            "inputTextDelta": input_text_delta,
        })

    @staticmethod
    def format_tool_input_available(tool_call_id: str, tool_name: str, input_data: Dict[str, Any]) -> str:
        return SSEFormatter.format({
            "type": "tool-input-available",
            "toolCallId": tool_call_id,
            "toolName": tool_name,
            "input": input_data,
        })

    @staticmethod
    def format_tool_output_available(tool_call_id: str, output: Dict[str, Any]) -> str:
        return SSEFormatter.format({
            "type": "tool-output-available",
            "toolCallId": tool_call_id,
            "output": output,
        })

    @staticmethod
    def format_finish() -> str:
        return SSEFormatter.format({"type": "finish"})

    @staticmethod
    def format_error(error_text: str) -> str:
        if not error_text:
            error_text = "An error occurred"
        return SSEFormatter.format({"type": "error", "errorText": error_text})

    @staticmethod
    def format_data_usage(usage: Dict[str, Any]) -> str:
        return SSEFormatter.format({"type": "data-usage", "data": usage})


class NormalizedToAISDK:
    """Convert normalized StreamEvent to AI SDK SSE format.

    Single formatter for all frameworks. Parsing is done in shared.events.
    """

    def __init__(self, session_id: str, agent_id: str, is_new_session: bool = False):
        self.session_id = session_id
        self.agent_id = agent_id
        self.is_new_session = is_new_session
        self.message_id = str(uuid.uuid4())
        self._accumulated_status: list[str] = []
        # Block IDs
        self._simple_text_id = f"text_{uuid.uuid4().hex[:8]}"
        self._simple_text_started = False
        self._processing_id = f"processing_{uuid.uuid4().hex[:8]}"
        self._processing_started = False
        self._thinking_id = f"thinking_{uuid.uuid4().hex[:8]}"
        self._thinking_started = False
        self._todos_id = f"todos_{uuid.uuid4().hex[:8]}"
        self._todos_started = False
        # Claude API format (indexed blocks)
        self._text_ids: dict[int, str] = {}
        self._thinking_ids: dict[int, str] = {}
        self._active_text: set[int] = set()
        self._active_thinking: set[int] = set()

    def format(self, event: StreamEvent) -> list[str]:
        out = []

        if event.type == EventType.STATUS:
            message = event.data.get("message", "")
            if message:
                if self._thinking_started:
                    out.append(SSEFormatter.format_reasoning_end(self._thinking_id))
                    self._thinking_started = False
                if not self._processing_started:
                    out.append(SSEFormatter.format_reasoning_start(self._processing_id, variant="processing"))
                    self._processing_started = True
                status_text = f"{message}\n"
                self._accumulated_status.append(status_text)
                out.append(SSEFormatter.format_reasoning_delta(self._processing_id, status_text))

        elif event.type == EventType.TODO_CREATE:
            items = event.data.get("items", [])
            if items:
                if self._todos_started:
                    out.append(SSEFormatter.format_reasoning_end(self._todos_id))
                out.append(SSEFormatter.format_reasoning_start(self._todos_id, variant="todos"))
                self._todos_started = True
                out.append(SSEFormatter.format_reasoning_delta(self._todos_id, json.dumps(items)))
                out.append(SSEFormatter.format_reasoning_end(self._todos_id))
                self._todos_started = False

        elif event.type == EventType.TODO_UPDATE:
            items = event.data.get("items", [])
            if items:
                if self._todos_started:
                    out.append(SSEFormatter.format_reasoning_end(self._todos_id))
                out.append(SSEFormatter.format_reasoning_start(self._todos_id, variant="todos"))
                self._todos_started = True
                out.append(SSEFormatter.format_reasoning_delta(self._todos_id, json.dumps(items)))
                out.append(SSEFormatter.format_reasoning_end(self._todos_id))
                self._todos_started = False

        elif event.type == EventType.TODO_DONE:
            item = event.data.get("item", {})
            content = item.get("content", "Task")[:50]
            if self._thinking_started:
                out.append(SSEFormatter.format_reasoning_end(self._thinking_id))
                self._thinking_started = False
            if not self._processing_started:
                out.append(SSEFormatter.format_reasoning_start(self._processing_id, variant="processing"))
                self._processing_started = True
            status_text = f"Completed: {content}...\n"
            out.append(SSEFormatter.format_reasoning_delta(self._processing_id, status_text))

        elif event.type == EventType.TEXT and event.index is not None:
            out.append(SSEFormatter.format_text_start(event.id or self._text_ids.get(event.index, "")))

        elif event.type == EventType.TEXT_DELTA:
            delta = event.data.get("delta") or event.data.get("content", "")
            if delta:
                if self._processing_started:
                    out.append(SSEFormatter.format_reasoning_end(self._processing_id))
                    self._processing_started = False
                if self._thinking_started:
                    out.append(SSEFormatter.format_reasoning_end(self._thinking_id))
                    self._thinking_started = False
                if event.index is None and not self._simple_text_started:
                    out.append(SSEFormatter.format_text_start(self._simple_text_id))
                    self._simple_text_started = True
                text_id = event.id or self._text_ids.get(event.index or 0) or self._simple_text_id
                out.append(SSEFormatter.format_text_delta(text_id, delta))

        elif event.type == EventType.THINKING:
            content = event.data.get("content", "")
            if content:
                if self._processing_started:
                    out.append(SSEFormatter.format_reasoning_end(self._processing_id))
                    self._processing_started = False
                if event.index is None:
                    if not self._thinking_started:
                        out.append(SSEFormatter.format_reasoning_start(self._thinking_id, variant="thinking"))
                        self._thinking_started = True
                    out.append(SSEFormatter.format_reasoning_delta(self._thinking_id, content))
                else:
                    out.append(SSEFormatter.format_reasoning_start(event.id or ""))

        elif event.type == EventType.THINKING_DELTA:
            if event.data.get("delta"):
                out.append(SSEFormatter.format_reasoning_delta(event.id or "", event.data["delta"]))

        elif event.type == EventType.TOOL_USE_START:
            tool_id = event.data.get("id", f"call_{uuid.uuid4().hex[:8]}")
            tool_name = event.data.get("name", "unknown")
            tool_input = event.data.get("input", {})
            out.append(SSEFormatter.format_tool_input_start(tool_id, tool_name))
            if tool_input:
                out.append(SSEFormatter.format_tool_input_available(tool_id, tool_name, tool_input))

        elif event.type == EventType.TOOL_RESULT:
            tool_id = event.data.get("tool_use_id", event.id) or (
                f"search_{uuid.uuid4().hex[:8]}" if "results" in event.data else None
            )
            if "results" in event.data:
                output = {
                    "count": event.data.get("count", 0),
                    "results": event.data.get("results", []),
                }
            else:
                output = event.data
            if tool_id and output:
                out.append(SSEFormatter.format_tool_output_available(tool_id, output))

        elif event.type == EventType.USAGE:
            usage = event.data.get("usage", {})
            if usage:
                out.append(SSEFormatter.format_data_usage({
                    "inputTokens": usage.get("input_tokens"),
                    "outputTokens": usage.get("output_tokens"),
                    "reasoningTokens": usage.get("reasoning_tokens"),
                    "cachedTokens": usage.get("cached_tokens"),
                    "stopReason": event.data.get("stop_reason"),
                    "isTotal": event.data.get("total", False),
                }))

        elif event.type == EventType.RESULT:
            data = event.data
            if data.get("is_error"):
                if self._simple_text_started:
                    out.append(SSEFormatter.format_text_end(self._simple_text_id))
                    self._simple_text_started = False
                out.append(SSEFormatter.format_error("Agent execution failed"))
            if data.get("total_cost_usd") is not None or data.get("duration_ms"):
                out.append(SSEFormatter.format_data_usage({
                    "totalCostUSD": data.get("total_cost_usd"),
                    "numTurns": data.get("num_turns"),
                    "durationMs": data.get("duration_ms"),
                    "sdkSessionId": data.get("session_id"),
                    "isError": data.get("is_error", False),
                }))

        elif event.type == EventType.ERROR:
            if self._simple_text_started:
                out.append(SSEFormatter.format_text_end(self._simple_text_id))
                self._simple_text_started = False
            error_message = event.data.get("message") or "Unknown error"
            out.append(SSEFormatter.format_error(error_message))

        return out

    def start(self) -> list[str]:
        return [SSEFormatter.format_start(self.message_id)]

    def end(self) -> list[str]:
        out = []
        if self._processing_started:
            out.append(SSEFormatter.format_reasoning_end(self._processing_id))
        if self._todos_started:
            out.append(SSEFormatter.format_reasoning_end(self._todos_id))
        if self._thinking_started:
            out.append(SSEFormatter.format_reasoning_end(self._thinking_id))
        for idx in list(self._active_text):
            out.append(SSEFormatter.format_text_end(self._text_ids.get(idx, "")))
        for idx in list(self._active_thinking):
            out.append(SSEFormatter.format_reasoning_end(self._thinking_ids.get(idx, "")))
        if self._simple_text_started:
            out.append(SSEFormatter.format_text_end(self._simple_text_id))
        out.append(SSEFormatter.format_finish())
        out.append(SSEFormatter.format_done())
        return out


def get_formatter(
    session_id: str,
    agent_id: str,
    is_new_session: bool = False,
    framework: str | None = None,
) -> NormalizedToAISDK:
    """Get formatter to convert normalized events to AI SDK format.

    Args:
        session_id: Mobox session ID
        agent_id: Agent identifier
        is_new_session: Whether this is a new session
        framework: Ignored (kept for API compatibility)
    """
    return NormalizedToAISDK(session_id, agent_id, is_new_session)
