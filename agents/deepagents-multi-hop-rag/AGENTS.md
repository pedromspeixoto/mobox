<Overview>
**Purpose:** Perform multi-hop RAG (Retrieval-Augmented Generation) tasks using Weaviate as the vector store.

**Architecture:**
- **Orchestrator** - Plans research, delegates to subagents, synthesizes findings
- **Research subagents** - Query Weaviate via RAG tool, reflect with `think_tool`

**Key files:**
- `agent.yaml` - Agent metadata, framework, entrypoint, env vars
- `run_agent.py` - Agent entrypoint, creates deep agent and streams events
- `tools/rag.py` - Weaviate vector search tool
- `tools/think_tool.py` - Reflection tool for surfacing reasoning
- `prompts/orchestrator.txt` - Orchestrator system prompt
- `prompts/researcher.txt` - Research subagent system prompt

**Tools:**
- `weaviate_search` - Multi-hop retrieval from Weaviate
- `think_tool` - Agent reflection (emits `think` events for frontend)
- `write_todos` - Planning (from harness)
- `task` - Subagent delegation (from harness)

## FastAPI Execution Flow

The agent is executed by the Mobox FastAPI API:

1. **Config loading** - `api/core/agents.py` loads `agent.yaml` from `agents/deepagents-multi-hop-rag/`
2. **AgentConfig** - Parses `name`, `description`, `framework`, `entrypoint`, `env_vars`, `timeout`, `idle_timeout`
3. **Sandbox spawn** - Chat route spawns a container with:
   - Image from `agent.yaml` (e.g. `docker.io/.../deepagents-multi-hop-rag:v0.0.1`)
   - Entrypoint: `["python", "/app/run_agent.py"]`
   - Env vars from `env_vars` (e.g. `OPENAI_API_KEY`) - values from server `.env`
   - Workspace with `prompt.txt` and optional `history.txt`
4. **Event streaming** - Agent emits JSON events to stdout → API parses via `DeepAgentsToAISDK` formatter → streams to frontend as AI SDK SSE

**agent.yaml fields used by API:**
- `framework: deepagents` - selects event formatter
- `entrypoint` - command run in sandbox
- `env_vars` - env var names to pass (must be in API's `ALLOWED_ENV_VARS` whitelist; values from server `.env`)

**Note:** If using Weaviate, add `WEAVIATE_HOST`, `WEAVIATE_API_KEY` (for cloud) to `env_vars` and to `ALLOWED_ENV_VARS` in `api/core/agents.py`.

## Event Emission

Agents emits raw agent events and, if needed for more control, JSON events via `shared/emitter.py`:

```python
emit("type", {"key": "value"})  # Generic
emit_text(content)              # Text chunks
emit_think(thought)             # Reflection (think_tool)
emit_status(message)            # Status updates
emit_error(message)             # Errors
emit_tool_use(id, name, args)   # Tool invocations
```

The API parses these through `api/core/event_formatters.py` and converts to AI SDK format. **Never** branch on raw `agent_event.type` in the API - use the normalized `StreamEvent` from the formatter.
</Overview>

<Skills>
You have a bunch of skills that you can use when prompted that help you with your tasks.

The skills are located under ../../.claude/skills.
</Skills>

<Framework>
This agent uses [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview) - a standalone library for building agents that handle complex, multi-step tasks. DeepAgents is built on LangGraph and provides planning, file system tools, and subagent spawning.

**When to use DeepAgents:**
- Complex, multi-step tasks requiring planning and decomposition
- Large context management via file system tools
- Delegating work to specialized subagents for context isolation
- Persisting memory across conversations and threads

**Relationship to LangChain ecosystem:**
- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) - graph execution and state management
- [LangChain](https://docs.langchain.com/oss/python/langchain/overview) – tools and model integrations
- [LangSmith](https://docs.langchain.com/langsmith/home) – observability and deployment
</Framework>

<Agent Harness>
The DeepAgents harness provides built-in tools and capabilities. See [Agent harness capabilities](https://docs.langchain.com/oss/python/deepagents/harness).

| Capability | Description |
|------------|-------------|
| **File system tools** | `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` - files as first-class citizens |
| **To-do list** | `write_todos` - track tasks with statuses (`pending`, `in_progress`, `completed`) |
| **Subagents** | `task` - spawn ephemeral subagents for isolated multi-step work |
| **Large result eviction** | `FilesystemMiddleware` evicts large tool results to prevent context overflow |
| **Conversation summarization** | Auto-compresses old history when token usage is high |
| **Dangling tool call repair** | Fixes message history when tool calls are interrupted |
| **Human-in-the-loop** | `interrupt_on` - pause at specified tools for approval |
| **Streaming** | Built-in streaming for main agent and subagents |

**Storage backends:**
- `StateBackend` - ephemeral in-memory (per thread)
- `FilesystemBackend` - real disk, supports sandboxed root
- `StoreBackend` - persistent via LangGraph BaseStore
- `CompositeBackend` - route paths to different backends
</Agent Harness>

<Best Practices>
- **Tool design** - Use `@tool` with clear docstrings; tools should be idempotent where possible
- **Prompt structure** - Use `load_prompt()` for templates; inject `{date}`, `{year}`, `{workspace}` as needed
- **Subagent delegation** - Default to 1 subagent; parallelize only for explicit comparisons or when asked to do so by the user.
- **Streaming** - Use `agent.astream()` with `stream_mode=["messages", "updates"]` for token + state updates
- **Error handling** - Emit `emit_error()` and `emit_warning()` for user-visible issues
</Best Practices>