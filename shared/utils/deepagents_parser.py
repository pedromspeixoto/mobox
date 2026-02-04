"""
DeepAgents parser for LangGraph/DeepAgents streams and invoke results.

Converts LangGraph events (AIMessageChunk, AIMessage, ToolMessage) into
a normalized event format: (type: str, data: dict).

Usage:
    emit = lambda t, d: print(json.dumps({"type": t, "data": d}))
    process_ai_chunk(chunk, emit)
    process_messages(messages, emit, ctx)
"""

import ast
import json
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

EmitFn = Callable[[str, dict[str, Any]], None]


@dataclass
class ParseContext:
    """Mutable context for message processing (token counts, subagent tracking)."""

    num_turns: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    active_subagents: set = field(default_factory=set)
    has_seen_write_todos: bool = False


def extract_messages(update: Any) -> list:
    """Extract messages list from LangGraph update (handles Overwrite, dict, etc.)."""
    if update is None:
        return []
    # Direct list (some LangGraph versions)
    if isinstance(update, list):
        return update
    if not isinstance(update, dict):
        return []
    messages = update.get("messages", [])
    if hasattr(messages, "value"):
        messages = messages.value
    if not isinstance(messages, list):
        return [messages] if messages else []
    return messages


def process_ai_chunk(chunk: AIMessageChunk, emit: EmitFn) -> None:
    """Process streaming AIMessageChunk and emit text, thinking, tool_call_start events."""
    if chunk.content:
        content = chunk.content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type == "thinking":
                        emit("thinking", {"content": block.get("thinking", "")})
                    elif block_type == "text":
                        text = block.get("text", "")
                        if text:
                            emit("text", {"content": text})
                    elif block_type == "tool_call_chunk" and block.get("name"):
                        emit("tool_call_start", {"id": block.get("id", ""), "name": block.get("name", "")})
                elif isinstance(block, str) and block:
                    emit("text", {"content": block})
        elif isinstance(content, str) and content:
            emit("text", {"content": content})

    if chunk.tool_call_chunks:
        for tc in chunk.tool_call_chunks:
            if tc.get("name"):
                emit("tool_call_start", {"id": tc.get("id", ""), "name": tc.get("name", "")})


def _parse_search_results(tool_content: Any) -> tuple[list, str | None]:
    """Parse weaviate/search tool result; returns (raw_results, corrected_query)."""
    raw_results = []
    corrected = None
    if isinstance(tool_content, dict):
        raw_results = tool_content.get("results", [])
        corrected = tool_content.get("_corrected_query")
    elif isinstance(tool_content, str):
        try:
            parsed = json.loads(tool_content)
            raw_results = parsed.get("results", [])
        except (json.JSONDecodeError, TypeError):
            try:
                parsed = ast.literal_eval(tool_content)
                raw_results = parsed.get("results", []) if isinstance(parsed, dict) else []
            except Exception:
                pass
    return raw_results, corrected


def process_messages(
    messages: list,
    emit: EmitFn,
    ctx: ParseContext,
    *,
    skip_ai_text: bool = False,
) -> None:
    """Process AIMessage and ToolMessage list; emit usage, model_info, tool events, text.

    When skip_ai_text=True (streaming context), do not emit text from AIMessage - it was
    already streamed via process_ai_chunk. This avoids duplicate content in the response.
    """
    for msg in messages:
        if isinstance(msg, AIMessage):
            ctx.num_turns += 1

            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                u = msg.usage_metadata
                ctx.total_input_tokens += u.get("input_tokens", 0)
                ctx.total_output_tokens += u.get("output_tokens", 0)
                emit("usage", {
                    "input_tokens": u.get("input_tokens", 0),
                    "output_tokens": u.get("output_tokens", 0),
                    "reasoning_tokens": u.get("output_token_details", {}).get("reasoning", 0),
                    "cached_tokens": u.get("input_token_details", {}).get("cache_read", 0),
                })

            if hasattr(msg, "response_metadata") and msg.response_metadata:
                model = msg.response_metadata.get("model_name", "")
                if model:
                    emit("model_info", {
                        "model": model,
                        "provider": msg.response_metadata.get("model_provider", ""),
                    })

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name", "")
                    args = tc.get("args", {})
                    if name == "write_todos":
                        items = args.get("todos", [])
                        if items:
                            if ctx.has_seen_write_todos:
                                emit("todo_update", {"items": items})
                            else:
                                ctx.has_seen_write_todos = True
                                emit("todo_create", {"items": items})
                    elif name == "task":
                        subagent = args.get("subagent_type", "unknown")
                        ctx.active_subagents.add(subagent)
                        emit("subagent_start", {"agent": subagent, "task": args.get("description", "")})
                    elif name == "think_tool" and args.get("thought"):
                        emit("think", {"id": tc.get("id", ""), "thought": args.get("thought", "")})
                    elif name in ("internet_search", "tavily_search"):
                        emit("search", {
                            "id": tc.get("id", ""),
                            "query": args.get("query", ""),
                            "topic": args.get("topic", "general"),
                        })
                    elif name in ("read_file", "write_file", "edit_file"):
                        emit("file_op", {
                            "id": tc.get("id", ""),
                            "operation": name.replace("_file", ""),
                            "path": args.get("file_path", args.get("path", "")),
                        })
                    else:
                        emit("tool_use", {"id": tc.get("id", ""), "name": name, "input": args})

            if msg.content and not skip_ai_text:
                content = msg.content
                if isinstance(content, str):
                    emit("text", {"content": content})
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            t = block.get("text", "")
                            if t:
                                emit("text", {"content": t})
                        elif isinstance(block, str) and block:
                            emit("text", {"content": block})

        elif isinstance(msg, ToolMessage):
            name = getattr(msg, "name", "")
            content = msg.content

            if name == "weaviate_search":
                raw_results, corrected = _parse_search_results(content)
                if corrected:
                    emit("search_corrected", {"query": corrected})
                results = [
                    {"title": r.get("title", "")[:80], "url": r.get("url", "")}
                    for r in raw_results[:5]
                    if isinstance(r, dict)
                ]
                emit("search_result", {"name": name, "count": len(raw_results), "results": results})
            elif name == "think_tool":
                emit("think_result", {"name": name, "acknowledged": True})
            elif name == "task":
                summary = ""
                if isinstance(content, str):
                    summary = content[:200] + "..." if len(content) > 200 else content
                elif isinstance(content, dict):
                    summary = content.get("summary", str(content)[:200])
                for sa in list(ctx.active_subagents):
                    emit("subagent_complete", {"agent": sa, "summary": summary})
                    ctx.active_subagents.discard(sa)
                    break
            else:
                emit("tool_result", {
                    "name": name,
                    "success": getattr(msg, "status", "") != "error",
                    "output_preview": str(content)[:200] if content else "",
                })
