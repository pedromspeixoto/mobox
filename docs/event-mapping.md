# Event Mapping: Agent Frameworks to AI SDK

This document explains how Mobox transforms events from different agent frameworks into the Vercel AI SDK streaming protocol for frontend consumption.

## Overview

Mobox supports multiple agent frameworks, each with its own streaming event format. Events flow through two stages: **parse** (shared lib) and **format** (API).

**Pattern (enforced):** Agents emit → shared parser normalizes → API converts to AI SDK. The chat route uses only normalized events; it must never branch on raw agent event types for business logic.

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Agent Framework   │     │   shared.events     │     │     API Layer       │
│                     │     │   (parse)           │     │     (format)        │
│  Claude / DeepAgents│ ──▶ │  Raw → StreamEvent  │ ──▶ │  StreamEvent →      │
│  / OpenAI / Gemini  │     │  Framework-specific │     │  AI SDK SSE         │
│                     │     │  parser             │     │  Single formatter   │
│  stdout: JSON lines │     │                     │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                                  │
                                                                  ▼
                                                         ┌─────────────────────┐
                                                         │  Frontend           │
                                                         │  AI SDK Client      │
                                                         │  useChat() hook     │
                                                         └─────────────────────┘
```

## Architecture

### Agent Level (stdout JSON events)

Agents run in isolated sandboxes and emit JSON events to stdout:

```json
{"type": "event_type", "data": {...}}
```

Each framework emits different event types, but they all follow this basic structure.

### Shared Lib (Parse: raw → normalized)

`shared/events.py` parses raw agent events into normalized `StreamEvent` format:

- `EventParser` – framework-specific parser (`claude`, `deepagents`, `langchain`)
- `get_parser(framework)` – returns parser for the given framework
- Parsing is the **single source of truth** for normalization

### API Level (Format: normalized → AI SDK)

`api/core/event_formatters.py` converts normalized events to AI SDK SSE:

- `NormalizedToAISDK` – single formatter for all frameworks
- No framework-specific logic; consumes only `StreamEvent`

### Frontend Level (AI SDK SSE)

The frontend receives Server-Sent Events (SSE) following the [Vercel AI SDK Stream Protocol](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol):

```
data: {"type": "start", ...}

data: {"type": "text-delta", ...}

data: {"type": "finish", ...}
```

---

## Event Types

### Normalized Event Types (Internal)

The API uses normalized event types internally before converting to AI SDK format:

| EventType | Description |
|-----------|-------------|
| `START` | Stream started |
| `DONE` | Stream completed |
| `ERROR` | Error occurred |
| `STATUS` | Status/progress message |
| `TEXT` | Text block started |
| `TEXT_DELTA` | Text content chunk |
| `THINKING` | Reasoning block started |
| `THINKING_DELTA` | Reasoning content chunk |
| `TOOL_USE_START` | Tool call initiated |
| `TOOL_USE_DELTA` | Tool input streaming |
| `TOOL_USE_END` | Tool call completed |
| `TOOL_RESULT` | Tool execution result |
| `USAGE` | Token usage data |
| `RESULT` | Final result with stats |
| `TODO_CREATE` | Todo list created |
| `TODO_UPDATE` | Todo list updated |
| `TODO_DONE` | Todo item completed |
| `RAW` | Pass-through event |

### AI SDK Event Types (Output)

Events sent to the frontend follow AI SDK format:

| AI SDK Event | Description |
|--------------|-------------|
| `start` | Message start with ID |
| `text-start` | Text part started |
| `text-delta` | Text content chunk |
| `text-end` | Text part completed |
| `reasoning-start` | Reasoning block started |
| `reasoning-delta` | Reasoning content chunk |
| `reasoning-end` | Reasoning block completed |
| `tool-input-start` | Tool call started |
| `tool-input-available` | Tool input ready |
| `tool-output-available` | Tool result ready |
| `data-usage` | Usage/metadata |
| `finish` | Message completed |
| `done` | Stream ended |
| `error` | Error occurred |

---

## Framework: Claude (claude)

### Agent Events (stdout)

Claude agents can emit events in two formats:

#### Claude API Streaming Format

```json
{"type": "message_start", "message": {"id": "...", "model": "..."}}
{"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}
{"type": "content_block_stop", "index": 0}
{"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {...}}
{"type": "message_stop"}
```

#### Simplified Agent SDK Format

```json
{"type": "start", "data": {"prompt_preview": "..."}}
{"type": "status", "data": {"message": "Analyzing..."}}
{"type": "text", "data": {"content": "Hello world"}}
{"type": "thinking", "data": {"content": "Let me think..."}}
{"type": "think", "data": {"thought": "Key insight from reflection..."}}
{"type": "tool_use", "data": {"id": "...", "name": "web_search", "input": {...}}}
{"type": "tool_result", "data": {"tool_use_id": "...", "content": "..."}}
{"type": "result", "data": {"session_id": "...", "duration_ms": 1234}}
{"type": "done", "data": {}}
```

### Event Mapping

| Claude Event | → | AI SDK Event |
|--------------|---|--------------|
| `message_start` | → | `start` |
| `content_block_start` (text) | → | `text-start` |
| `content_block_delta` (text_delta) | → | `text-delta` |
| `content_block_stop` | → | `text-end` |
| `content_block_start` (thinking) | → | `reasoning-start` |
| `content_block_delta` (thinking_delta) | → | `reasoning-delta` |
| `content_block_start` (tool_use) | → | `tool-input-start` |
| `content_block_delta` (input_json_delta) | → | (accumulated) |
| `content_block_stop` (tool) | → | `tool-input-available` |
| `message_delta` (usage) | → | `data-usage` |
| `message_stop` | → | `finish`, `done` |
| `error` | → | `error` |
| --- | --- | --- |
| `start` (simplified) | → | `start` |
| `status` | → | `reasoning-delta` (processing block) |
| `text` | → | `text-delta` |
| `thinking` | → | `reasoning-delta` (thinking block) |
| `think` | → | `reasoning-delta` (think tool, accumulated) |
| `tool_use` | → | `tool-input-start`, `tool-input-available` |
| `tool_result` | → | `tool-output-available` |
| `todo_create`, `todo_update` | → | `reasoning-delta` (todos block) |
| `subagent_spawn` | → | `reasoning-delta` (processing block) |
| `result` | → | `data-usage` |
| `done` | → | `finish`, `done` |

**TodoWrite tool**: When the Claude agent uses the built-in TodoWrite tool, `claude_parser` maps it to `todo_update` so the frontend shows the same "N steps" progress UI as DeepAgents.

**subagent_spawn**: Emitted by SubagentTracker when Task spawns a subagent; mapped to status message in processing block.

### Special Handling

- **Status messages**: Grouped into a collapsible "processing" block rendered as reasoning
- **Thinking content**: Rendered as collapsible reasoning blocks
- **Tool calls**: Input streamed incrementally, output emitted when complete

---

## Framework: DeepAgents (deepagents)

### Agent Events (stdout)

DeepAgents uses the simplified event format with additional events for orchestration:

```json
{"type": "start", "data": {"prompt_preview": "...", "architecture": "orchestrator_subagent"}}
{"type": "status", "data": {"message": "DeepAgents Research Agent starting..."}}
{"type": "todo_create", "data": {"items": [{"content": "Research topic A", "status": "pending"}]}}
{"type": "subagent_start", "data": {"agent": "research-agent", "task": "Research AI safety"}}
{"type": "search", "data": {"id": "...", "query": "AI safety 2024", "topic": "general"}}
{"type": "search_result", "data": {"count": 5, "results": [{"title": "...", "url": "..."}]}}
{"type": "think", "data": {"id": "...", "thought": "Found 3 relevant sources..."}}
{"type": "subagent_complete", "data": {"agent": "research-agent", "summary": "..."}}
{"type": "text", "data": {"content": "# Research Report\n\n..."}}
{"type": "usage", "data": {"input_tokens": 1000, "output_tokens": 500}}
{"type": "usage_total", "data": {"input_tokens": 5000, "output_tokens": 2500}}
{"type": "result", "data": {"duration_ms": 45000, "num_turns": 12}}
{"type": "done", "data": {}}
```

### Event Mapping

| DeepAgents Event | → | AI SDK Event | Block Type |
|------------------|---|--------------|------------|
| `start` | → | `start` | - |
| `status` | → | `reasoning-delta` | Processing |
| `text` | → | `text-delta` | Text |
| `thinking` | → | `reasoning-delta` | Thinking |
| `think` | → | `reasoning-delta` | Thinking |
| `todos`, `todo_create` | → | `reasoning-delta` | Processing (TODO_CREATE) |
| `todo_update` | → | `reasoning-delta` | Processing (TODO_UPDATE) |
| `todo_done` | → | `reasoning-delta` | Processing (TODO_DONE) |
| `subagent_start` | → | `reasoning-delta` | Thinking |
| `subagent_complete` | → | `reasoning-delta` | Thinking |
| `search` | → | `tool-input-start`, `tool-input-available` | - |
| `search_result` | → | `tool-output-available` | - |
| `tool_use` | → | `tool-input-start`, `tool-input-available` | - |
| `tool_result` | → | `tool-output-available` | - |
| `usage` | → | `data-usage` | - |
| `usage_total` | → | `data-usage` (with isTotal flag) | - |
| `result` | → | `data-usage` (with stats) | - |
| `error` | → | `error` | - |
| `done` | → | `finish`, `done` | - |

### Special Handling

- **Orchestrator pattern**: Status messages (`status`, `todos`) show orchestrator activity in Processing block
- **Subagent events**: `subagent_start` and `subagent_complete` are rendered in Thinking block to show agent activity as part of the "thinking" process
- **Think tool**: Agent reflections from `emit_think()` rendered as Thinking content (accumulated for persistence)
- **Todo planning**: Shown as part of Processing status
- **Search events**: Mapped to tool calls with query as input

### Block Ordering

The formatter manages block ordering to ensure clean UI:

1. Processing blocks (status, todos) appear during orchestrator activity
2. Thinking blocks (subagent events, think tool output) appear during research/reasoning
3. Text blocks (final response) appear last

**Block Transitions:**

- When a THINKING event arrives while Processing is open → Processing closes, Thinking opens
- When a STATUS event arrives while Thinking is open → Thinking closes, Processing opens
- When TEXT arrives → All reasoning blocks close, Text opens

This ensures subagent activity and agent reflections are grouped together in the Thinking block.

---

## Event Consistency Across Frameworks

The shared parser (`shared/events.py`) and single formatter (`api/core/event_formatters.py`) support a common set of normalized events. This allows agents to use the same emitter functions regardless of framework.

### Shared Events (Both Formatters)

| Agent Event | Normalized Type | Accumulates | AI SDK Output | Notes |
|-------------|-----------------|-------------|---------------|-------|
| `start` | START | - | `start` | Stream initialization |
| `status` | STATUS | `_accumulated_status` | `reasoning-delta` (processing) | Orchestrator activity |
| `text` | TEXT_DELTA | `_accumulated_text` | `text-delta` | Final response content |
| `thinking` | THINKING | `_accumulated_thinking` | `reasoning-delta` (thinking) | Explicit thinking content |
| `think` | THINKING | `_accumulated_thinking` | `reasoning-delta` (thinking) | Think tool output |
| `tool_use` | TOOL_USE_START | - | `tool-input-start/available` | Tool invocation |
| `tool_result` | TOOL_RESULT | - | `tool-output-available` | Tool output |
| `error` | ERROR | - | `error` | Error message |
| `done` | DONE | - | `finish`, `done` | Stream completion |

### DeepAgents-Only Events

| Agent Event | Normalized Type | Accumulates | Notes |
|-------------|-----------------|-------------|-------|
| `subagent_start` | THINKING | `_accumulated_thinking` | Subagent spawned |
| `subagent_complete` | THINKING | `_accumulated_thinking` | Subagent finished |
| `search` | TOOL_USE_START | - | Mapped to `internet_search` tool |
| `search_result` | TOOL_RESULT | - | Search results |
| `todos`, `todo_create` | TODO_CREATE | - | Planning/todo list created |
| `todo_update` | TODO_UPDATE | - | Todo list updated |
| `todo_done` | TODO_DONE | - | Todo item completed |
| `tool_call_start` | TOOL_USE_START | - | Alternative tool start format |
| `usage` | USAGE | - | Token usage |
| `usage_total` | USAGE | - | Total usage (multi-turn) |

### Claude-Only Events (API Format)

| Claude Event | Normalized Type | Notes |
|--------------|-----------------|-------|
| `message_start` | START | Claude API stream start |
| `content_block_start` | TEXT / THINKING / TOOL_USE_START | Indexed content blocks |
| `content_block_delta` | TEXT_DELTA / THINKING_DELTA / TOOL_USE_DELTA | Streaming deltas |
| `content_block_stop` | TOOL_USE_END | Block completion |
| `message_delta` | USAGE | Usage stats |
| `message_stop` | DONE | Stream end |

### Adding New Event Types

When adding a new event type that should work across all agents:

1. Add parse logic in `shared/events.py` for both `_parse_claude` and `_parse_deepagents`
2. Map to normalized EventType (e.g. `EventType.THINKING`)
3. If it should accumulate for persistence, append to `_accumulated_text` or `_accumulated_thinking`
4. Add format handling in `api/core/event_formatters.py` (NormalizedToAISDK.format) if needed

Example - adding a new `reflect` event:

```python
# In shared/events.py, in both _parse_claude and _parse_deepagents:
if event_type == "reflect":
    content = data.get("content", "")
    self._accumulated_thinking.append(content)
    return StreamEvent(type=EventType.THINKING, data={"content": content, "source": "reflect"})
```

---

## Framework: OpenAI (Future)

### Planned Agent Events

```json
{"type": "start", "data": {"model": "gpt-4"}}
{"type": "delta", "data": {"content": "Hello"}}
{"type": "tool_call", "data": {"id": "...", "name": "...", "arguments": "..."}}
{"type": "tool_result", "data": {"id": "...", "content": "..."}}
{"type": "done", "data": {"usage": {...}}}
```

### Planned Mapping

| OpenAI Event | → | AI SDK Event |
|--------------|---|--------------|
| `start` | → | `start` |
| `delta` | → | `text-delta` |
| `tool_call` | → | `tool-input-start`, `tool-input-available` |
| `tool_result` | → | `tool-output-available` |
| `done` | → | `data-usage`, `finish`, `done` |

---

## Framework: Gemini (Future)

### Planned Agent Events

```json
{"type": "start", "data": {"model": "gemini-pro"}}
{"type": "content", "data": {"text": "Hello"}}
{"type": "function_call", "data": {"name": "...", "args": {...}}}
{"type": "function_response", "data": {"name": "...", "response": {...}}}
{"type": "done", "data": {"usage": {...}}}
```

### Planned Mapping

| Gemini Event | → | AI SDK Event |
|--------------|---|--------------|
| `start` | → | `start` |
| `content` | → | `text-delta` |
| `function_call` | → | `tool-input-start`, `tool-input-available` |
| `function_response` | → | `tool-output-available` |
| `done` | → | `data-usage`, `finish`, `done` |

---

## Adding a New Framework

To add support for a new agent framework:

### 1. Define Agent Event Format

Document the events your agent will emit to stdout:

```python
# In your agent's run_agent.py
from shared.emitter import emit, emit_text, emit_done

emit("start", {"model": "your-model"})
emit_text("Hello world")
emit("tool_use", {"id": "...", "name": "...", "input": {...}})
emit_done()
```

### 2. Add Parser in Shared Lib

Add parse logic in `shared/events.py`:

```python
# In EventParser.parse(), add framework branch:
def parse(self, raw_event: dict[str, Any]) -> StreamEvent:
    if self.framework == "your_framework":
        return self._parse_your_framework(raw_event)
    # ...

def _parse_your_framework(self, raw_event: dict[str, Any]) -> StreamEvent:
    event_type = raw_event.get("type", "unknown")
    data = raw_event.get("data", {})
    if event_type == "your_text_event":
        self._accumulated_text.append(data.get("content", ""))
        return StreamEvent(type=EventType.TEXT_DELTA, data={"delta": data.get("content", "")})
    # ... handle other events, map to EventType
```

### 3. Register the Framework

In `EventParser.parse()`, add the framework branch that calls your parser method. The single `NormalizedToAISDK` formatter handles all EventTypes—no API changes needed.

### 4. Configure Agent

Set the framework in your agent's `agent.yaml`:

```yaml
name: Your Agent
framework: your_framework
# ...
```

---

## SSE Format Reference

### AI SDK SSE Structure

Each SSE event follows this format:

```
data: {"type": "event-type", ...event-specific-data}\n\n
```

### Common Events

#### Start

```
data: {"type": "start", "messageId": "msg_abc123"}\n\n
```

#### Text Streaming

```
data: {"type": "text-start", "id": "text_1"}\n\n
data: {"type": "text-delta", "id": "text_1", "delta": "Hello "}\n\n
data: {"type": "text-delta", "id": "text_1", "delta": "world!"}\n\n
data: {"type": "text-end", "id": "text_1"}\n\n
```

#### Reasoning/Thinking

```
data: {"type": "reasoning-start", "id": "thinking_1"}\n\n
data: {"type": "reasoning-delta", "id": "thinking_1", "delta": "Let me analyze..."}\n\n
data: {"type": "reasoning-end", "id": "thinking_1"}\n\n
```

#### Tool Calls

```
data: {"type": "tool-input-start", "id": "call_1", "name": "web_search"}\n\n
data: {"type": "tool-input-available", "id": "call_1", "name": "web_search", "input": {"query": "AI news"}}\n\n
data: {"type": "tool-output-available", "id": "call_1", "output": {"results": [...]}}\n\n
```

#### Usage Data

```
data: {"type": "data-usage", "usage": {"inputTokens": 100, "outputTokens": 50}}\n\n
```

#### Completion

```
data: {"type": "finish"}\n\n
data: {"type": "done"}\n\n
```

#### Error

```
data: {"type": "error", "error": "Something went wrong"}\n\n
```

---

## Complete Flow: Agent → Storage → UI

This section documents the full lifecycle of events from agent emission through database storage to frontend rendering.

### 1. Agent Event Emission

Agents emit events to stdout using the shared emitter (`shared/emitter.py`):

```python
# Status events - system activity
emit_status("Starting agent...")           # → {"type": "status", "data": {"message": "..."}}
emit_subagent_start("researcher", "task")  # → {"type": "subagent_start", "data": {...}}
emit_subagent_complete("researcher", "...")# → {"type": "subagent_complete", "data": {...}}

# Think events - agent reasoning (from think_tool)
emit_think("Key findings so far...")       # → {"type": "think", "data": {"thought": "..."}}

# Text events - final response
emit_text("Here is the report...")         # → {"type": "text", "data": {"content": "..."}}
```

### 2. Parser & Formatter Processing

The parser (`shared/events.py`) accumulates text/thinking. The formatter (`api/core/event_formatters.py`) converts to AI SDK and tracks block state:

| Agent Event | Normalized Type | Accumulates To | Reasoning Block ID | Block Variant |
|-------------|-----------------|----------------|-------------------|---------------|
| `status` | `STATUS` | `_accumulated_status[]` | `_processing_id` | `processing` |
| `todos`, `todo_create` | `TODO_CREATE` | - | `_processing_id` | `processing` |
| `todo_update` | `TODO_UPDATE` | - | `_processing_id` | `processing` |
| `todo_done` | `TODO_DONE` | - | `_processing_id` | `processing` |
| `think` | `THINKING` | `_accumulated_thinking[]` | `_thinking_id` | `thinking` |
| `thinking` | `THINKING` | `_accumulated_thinking[]` | `_thinking_id` | `thinking` |
| `subagent_start` | `THINKING` | `_accumulated_thinking[]` | `_thinking_id` | `thinking` |
| `subagent_complete` | `THINKING` | `_accumulated_thinking[]` | `_thinking_id` | `thinking` |
| `text` | `TEXT_DELTA` | `_accumulated_text[]` | `_simple_text_id` | - |

**Block State Management:**

The formatter tracks which blocks are open and closes/opens them as needed:

```
STATUS event     → if thinking open: close it → open/continue processing block
THINKING event   → if processing open: close it → open/continue thinking block  
TEXT event       → close all reasoning blocks → open text block
```

**SSE Output with Variant Metadata:**

```python
# Processing block
SSEFormatter.format_reasoning_start(processing_id, variant="processing")
# → {"type": "reasoning-start", "id": "processing_xxx", "providerMetadata": {"mobox": {"variant": "processing"}}}

# Thinking block  
SSEFormatter.format_reasoning_start(thinking_id, variant="thinking")
# → {"type": "reasoning-start", "id": "thinking_xxx", "providerMetadata": {"mobox": {"variant": "thinking"}}}
```

### 3. Database Storage

When streaming completes, `api/routes/chat.py` saves accumulated content:

```python
# Get accumulated content from parser (accumulated during parse)
content = parser.get_text()              # Joined _accumulated_text
thinking = parser.get_thinking()         # Joined _accumulated_thinking

# Build message metadata
message_metadata = {}
if accumulated_status:
    message_metadata["processing"] = accumulated_status  # List[str]
if thinking:
    message_metadata["thinking"] = thinking              # str

# Save to database
assistant_message = ChatMessage(
    id=uuid,
    chat_id=session_id,
    role="assistant",
    content=content,                      # Final text response
    message_metadata=message_metadata,    # {"processing": [...], "thinking": "..."}
)
```

**Database Schema (ChatMessage):**

| Column | Type | Content |
|--------|------|---------|
| `id` | UUID | Message identifier |
| `content` | TEXT | Final response text |
| `message_metadata` | JSONB | `{"processing": ["msg1", "msg2"], "thinking": "..."}` |

### 4. Frontend Loading from History

When loading messages from database (`page.tsx` / `chat.tsx`):

```typescript
const parts: ChatMessage["parts"] = [];

// Processing block (from metadata.processing)
const processing = msg.metadata?.processing as string[] | undefined;
if (processing && processing.length > 0) {
  parts.push({
    type: "reasoning",
    text: processing.join("\n"),
    providerMetadata: { mobox: { variant: "processing" } },
  });
}

// Thinking block (from metadata.thinking)
const thinking = msg.metadata?.thinking as string | undefined;
if (thinking) {
  parts.push({
    type: "reasoning",
    text: thinking,
    providerMetadata: { mobox: { variant: "thinking" } },
  });
}

// Text content (from content field)
if (msg.content) {
  parts.push({ type: "text", text: msg.content });
}
```

### 5. Frontend Rendering

**message.tsx** - Iterates over parts and renders reasoning blocks:

```tsx
// Filter and render reasoning parts
{message.parts
  .filter(p => p.type === "reasoning" && p.text?.trim())
  .map((part, index) => {
    const variant = part.providerMetadata?.mobox?.variant;
    return (
      <MessageReasoning
        reasoning={part.text}
        variant={variant}  // "processing" | "thinking"
      />
    );
  })}

// Render text parts
{message.parts
  .filter(p => p.type === "text")
  .map(part => <Response>{part.text}</Response>)}
```

**message-reasoning.tsx** - Renders based on variant:

```tsx
const isProcessing = variant === "processing";

return (
  <div className={isProcessing ? "bg-muted/20" : "bg-muted/40"}>
    {isProcessing ? (
      <ProcessingTrigger />  // "Processed in Xs" with checkmark icon
    ) : (
      <ReasoningTrigger />   // "Thought for Xs" with brain icon
    )}
    <ReasoningContent>{reasoning}</ReasoningContent>
  </div>
);
```

### Event Type Summary

| Event Source | Emit Function | Storage Location | UI Block | Trigger Label |
|--------------|---------------|------------------|----------|---------------|
| Status messages | `emit_status()` | `metadata.processing[]` | Processing | "Processed in Xs" |
| Todo planning | `emit_todo_create()`, `emit_todo_update()`, `emit_todo_done()` | `metadata.processing[]` | Processing | "Processed in Xs" |
| Subagent start | `emit_subagent_start()` | `metadata.thinking` | Thinking | "Thought for Xs" |
| Subagent complete | `emit_subagent_complete()` | `metadata.thinking` | Thinking | "Thought for Xs" |
| Think tool | `emit_think()` | `metadata.thinking` | Thinking | "Thought for Xs" |
| Thinking content | `emit("thinking")` | `metadata.thinking` | Thinking | "Thought for Xs" |
| Final response | `emit_text()` | `content` | Text | (no trigger) |

### UI Display Scenarios

**During Streaming:**

1. Status events arrive → Processing block opens, shows "Processing..."
2. Think events arrive → Processing closes, Thinking block opens, shows "Thinking..."
3. More think events → Appended to same Thinking block
4. Status events arrive → Thinking closes, Processing reopens
5. Text events arrive → All reasoning closes, text streams below

**From History (Page Load/Refresh):**

1. If `metadata.processing` exists → Render collapsed Processing block
2. If `metadata.thinking` exists → Render collapsed Thinking block
3. If `content` exists → Render text response

**Block Behavior:**

- Blocks auto-collapse 500ms after streaming ends
- When newer block appears, older blocks collapse via `hasNewerBlock` prop
- User can manually expand/collapse by clicking trigger
- Duration tracked and displayed (e.g., "Thought for 5s")

---

## Files Reference

### Backend

| File | Purpose |
|------|---------|
| `shared/events.py` | EventParser – parse raw events to StreamEvent (framework-specific) |
| `api/core/event_formatters.py` | NormalizedToAISDK – single formatter, StreamEvent → AI SDK SSE |
| `api/core/sse.py` | SSE formatting utilities (AI SDK protocol) |
| `api/core/agents.py` | Agent config loading |
| `api/routes/chat.py` | Chat endpoint with streaming |
| `shared/emitter.py` | Agent event emission helpers (emit_text, emit_think, etc.) |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/components/message.tsx` | Message rendering, extracts variant from providerMetadata |
| `frontend/components/message-reasoning.tsx` | Reasoning block rendering (Processing vs Thinking) |
| `frontend/components/elements/reasoning.tsx` | Collapsible logic with duration tracking |
| `frontend/components/elements/processing-trigger.tsx` | "Processed in Xs" trigger UI |
| `frontend/app/(chat)/chat/[chatId]/page.tsx` | Loads messages from DB, reconstructs reasoning parts |
| `frontend/components/chat.tsx` | Older message loading with reasoning reconstruction |

---

## Debugging

### Agent Logs

Agent stdout is captured and can be viewed in Modal dashboard or local logs.

### Formatter State

The parser accumulates text/thinking for persistence. The formatter tracks open blocks to ensure proper event ordering.
