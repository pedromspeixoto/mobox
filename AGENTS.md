# Mobox Agent Context

> **Important**: Whenever you discover or implement something relevant to keep in context for future improvements, add it to this file.

## Architecture

### Event Streaming Pipeline

Mobox uses a three-layer architecture for streaming agent responses to the frontend:

```
Agents (stdout JSON) → shared (parse) → API (format) → Frontend (AI SDK SSE)
```

**Pattern (ALWAYS follow):**
1. **Agents** emit events via `shared/emitter.py` – framework-specific format (Claude, DeepAgents, etc.)
2. **Shared** parses via `shared/events.py` → normalizes to `StreamEvent` (EventType + data)
3. **API** converts normalized events to AI SDK format via single formatter → streams to frontend

The parser is the **single source of truth** for normalization. The chat route must:
- Parse every agent event through `parser.parse()` first (from `shared.events`)
- Use only the normalized `StreamEvent` for collection (usage, status, etc.) and persistence (ChatEvent)
- Never branch on raw `agent_event.type` or `agent_event.data` for business logic

**Key files:**
- `shared/emitter.py` - Agent event emission helpers
- `shared/events.py` - Parse raw events → StreamEvent (EventType, EventParser, get_parser)
- `shared/utils/deepagents_parser.py` - Parse LangGraph/DeepAgents output (used by agents)
- `shared/utils/claude_parser.py` - Parse Claude SDK messages (used by agents)
- `api/core/event_formatters.py` - Convert StreamEvent → AI SDK SSE (single NormalizedToAISDK)
- `api/routes/chat.py` - Uses parser + formatter; consumes only normalized events
- `docs/event-mapping.md` - Full event mapping documentation

**Design decision: Parse in shared lib, format in API**

1. **Parse in shared** - Both API and future CLI/mobile can use the same normalization
2. **Single formatter** - API has one NormalizedToAISDK; no framework-specific format logic
3. **Agent simplicity** - Agents emit natural events for their framework
4. **Decoupling** - Agents don't know/care about frontend technology

**Supported frameworks:**
- `claude` - Claude Agent SDK / Anthropic API events. Uses built-in TodoWrite tool for progress UI (mapped to todo_create/todo_update). SubagentTracker emits subagent_spawn → status.
- `deepagents` / `langchain` - LangChain DeepAgents events

**Adding a new framework:**
1. Define agent event format (emit via `shared/emitter.py`)
2. Add parse logic in `shared/events.py` (EventParser._parse_*)
3. Set `framework: your_framework` in agent's `agent.yaml`

### DeepAgents Research Agent - Orchestrator Pattern

The `deepagents-simple-research` agent uses an orchestrator + subagent pattern:

**Key files:**
- `agents/deepagents-simple-research/run_agent.py` - Orchestrator with subagent spawning
- `agents/deepagents-simple-research/prompts/orchestrator.txt` - Coordination instructions
- `agents/deepagents-simple-research/prompts/researcher.txt` - Research sub-agent instructions
- `agents/deepagents-simple-research/tools/think_tool.py` - Reflection tool for sub-agents

**Pattern:**
1. Orchestrator plans research via `write_todos` (emits `todo_create`, `todo_update`, `todo_done`)
2. Orchestrator delegates to research sub-agents via `task()` tool
3. Sub-agents search (Tavily) and reflect (think_tool)
4. Orchestrator synthesizes findings into final report

**Todo events** (from `shared/emitter.py`):
- `emit_todo_create(items)` – new todo list created
- `emit_todo_update(items)` – list updated
- `emit_todo_done(item, index)` – item completed

**Agent prompt requirement:** Orchestrator prompts MUST instruct the agent to call `write_todos` again whenever task status changes (before delegating → in_progress; after task completes → completed; before final report → all completed). See `deepagents-*/prompts/orchestrator.txt` for the "TODO Updates" section.

**Delegation strategy (from orchestrator prompt):**
- Default to 1 sub-agent for most queries
- Only parallelize for explicit comparisons (e.g., "Compare A vs B")
- Max 3 parallel sub-agents per iteration

### Surfacing Agent Reasoning via Think Tool

**Problem:** In orchestrator + subagent patterns, the subagent's internal activity doesn't appear in the orchestrator's stream. LangGraph runs subagents as nested executions, only returning the final result. Users see no feedback during the research process.

**Solution:** Use a `think_tool` that emits `think` events with the agent's reasoning.

The think tool follows Anthropic's "Claude Think Tool" pattern - agents pause to reflect on their progress, and those reflections are streamed to the user as "Thinking" blocks:

```python
# tools/think_tool.py
from shared.emitter import emit

@tool
def think_tool(thought: str) -> str:
    """Agent reflects on research progress - what was found, what's missing, next steps."""
    emit("think", {"id": f"think_{uuid.uuid4().hex[:8]}", "thought": thought})
    return "Thought recorded..."
```

The agent's prompt instructs it to use `think_tool` after every search to analyze results and plan next steps. This creates a natural "AI thinking" experience where users see:

- What information was found
- What gaps remain  
- Assessment of progress
- Next steps being planned

**Why this approach (not tool-specific events):**
- Natural language reasoning is more meaningful than structured tool events
- Users see the agent's actual decision-making process
- Single event type (`think`) keeps the system simple
- Thinking content describes actions implicitly ("Searching for X...", "Found 3 sources about Y...")

**Frontend rendering:**
- `think` events → `THINKING` type → "Thought for Xs" collapsible block
- Appears separately from "Processed in Xs" status messages
- Auto-collapses when complete, user can expand to review

## Frontend

### Reasoning/Processing Blocks - Auto-Collapse Behavior

The `MessageReasoning` component renders collapsible blocks for processing and thinking content.

**Key files:**
- `frontend/components/message-reasoning.tsx` - Wrapper that determines block type and manages collapse state
- `frontend/components/elements/reasoning.tsx` - Core collapsible logic with duration tracking
- `frontend/components/elements/processing-trigger.tsx` - Processing block trigger UI
- `frontend/components/message.tsx` - Parent that renders message parts

**Behavior:**
1. **Auto-collapse on completion**: Blocks auto-collapse 500ms after streaming ends (`AUTO_CLOSE_DELAY` in `reasoning.tsx`)
2. **Collapse when newer block appears**: When a thinking block starts, preceding processing blocks collapse automatically via `hasNewerBlock` prop
3. **Duration tracking**: Blocks track and display how long they were active (e.g., "Processed in 3s", "Thought for 5s")

**State flow:**
- `isLoading` prop indicates if the message is still streaming
- `hasNewerBlock` prop indicates if a newer reasoning block exists after this one
- `isActivelyStreaming = isLoading && !hasNewerBlock` - determines if this specific block is the active one

**Content detection:**
- Processing content: matches patterns like "creating sandbox", "starting agent", "initializing", etc.
- Thinking content: everything else (actual reasoning/thought process)

**Possible improvements:**
- [ ] Add animation when collapsing
- [ ] Allow user preference to keep blocks expanded
- [ ] Persist expand/collapse state per session

### Local Agent Development (Subprocess Sandbox)

With `SANDBOX_BACKEND=subprocess`, agents run locally via `uv run python run_agent.py`. Agents depend on the `shared` package (`shared/`).

**After pulling changes to `shared/`** (at project root), run `make sync-agents` to reinstall the shared package in all agents. Otherwise agents may crash with `TypeError: process_messages() got an unexpected keyword argument 'skip_ai_text'` or similar.

### Stream Resumption (Redis)

Follows [AI SDK Chatbot Resume Streams](https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams). When `REDIS_URL` is set, streams survive page refresh via `resumable-stream` and `GET /api/chat/[id]/stream`.

**Setup**: `REDIS_URL=redis://localhost:6379`, `docker compose up -d redis`. See `docs/stream-resumption.md`.

