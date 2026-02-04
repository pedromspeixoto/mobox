"""
DeepAgents Research Agent with Subagent Orchestration.

Documentation - https://docs.langchain.com/oss/python/deepagents/overview

This module creates a deep research agent following the orchestrator + subagent
pattern from the LangChain deepagents examples. The orchestrator coordinates
research by delegating to specialized research sub-agents.

Architecture:
- Orchestrator: Plans research, delegates to sub-agents, synthesizes findings
- Research Sub-agents: Conduct web searches with reflection (think tool)
"""

import ast
import os
import sys
import json
import asyncio
import time
from pathlib import Path

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from shared.emitter import (
    emit,
    emit_status,
    emit_error,
    emit_warning,
    emit_result,
    emit_done,
)
from shared.load_prompt import load_prompt
from shared.utils import (
    ParseContext,
    extract_messages,
    process_ai_chunk,
    process_messages,
)
from tools.tavily_search import internet_search
from tools.think_tool import think_tool

# Paths to prompt files
PROMPTS_DIR = Path(__file__).parent / "prompts"


async def run_agent(prompt: str, workspace: str, _history: list = None) -> None:
    """Execute the research agent with orchestrator + subagent pattern.

    Args:
        prompt: The user prompt to send to the agent
        workspace: Working directory for file operations
        history: Optional list of previous conversation messages
    """

    # Load prompts for all agents (inject workspace path and date)
    orchestrator_prompt = load_prompt("orchestrator.txt", workspace, PROMPTS_DIR)
    researcher_prompt = load_prompt("researcher.txt", workspace, PROMPTS_DIR)

    # Specify models
    orchestrator_model = init_chat_model(model="openai:gpt-4o-mini")
    researcher_model = init_chat_model(model="openai:gpt-4o-mini")

    # Define research sub-agent
    research_sub_agent = {
        "name": "research-agent",
        "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
        "system_prompt": researcher_prompt,
        "tools": [internet_search, think_tool],
        "model": researcher_model,
    }

    # Define backend for deepagent
    # Backend will be a storage - this storage will be then persisted to a remote bucket
    # TODO - define bucket where it will live

    # Create orchestrator agent with subagents
    agent = create_deep_agent(
        name="orchestrator",
        model=orchestrator_model,
        system_prompt=orchestrator_prompt,
        subagents=[research_sub_agent],
    )

    start_time = time.time()
    ctx = ParseContext()

    # Emit start event
    emit("start", {
        "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
        "has_history": _history is not None,
        "architecture": "orchestrator_subagent",
    })

    # Use stream with multiple modes for better structured output
    # - "messages": Token streaming with metadata
    # - "updates": State updates after each step (tool results, etc.)
    async for stream_mode, data in agent.astream(
        {"messages": [{"role": "user", "content": prompt}]},
        stream_mode=["messages", "updates"],
    ):
        if stream_mode == "messages":
            token, _ = data
            if isinstance(token, AIMessageChunk):
                process_ai_chunk(token, emit)
        elif stream_mode == "updates":
            for node_name, update in data.items():
                if node_name == "__interrupt__":
                    emit("interrupt", {"data": str(update)[:200]})
                    continue
                messages = extract_messages(update)
                if messages:
                    process_messages(messages, emit, ctx, skip_ai_text=True)
                if node_name in ("model", "tools"):
                    emit("step_complete", {"node": node_name})

    # Emit final result with session statistics
    duration_ms = int((time.time() - start_time) * 1000)
    emit_result(
        session_id="",
        duration_ms=duration_ms,
        num_turns=ctx.num_turns,
        is_error=False,
        total_cost_usd=None,
    )

    # Emit total usage summary
    emit("usage_total", {
        "input_tokens": ctx.total_input_tokens,
        "output_tokens": ctx.total_output_tokens,
        "total_tokens": ctx.total_input_tokens + ctx.total_output_tokens,
    })

    emit_done()


def main():
    # Load .env file if available (for local development)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, skip (production/container)

    import argparse
    parser = argparse.ArgumentParser(description="Run DeepAgents Research Agent with Subagent Orchestration")
    parser.add_argument(
        "--prompt",
        type=str,
        help="Prompt to send to the agent (overrides prompt.txt)"
    )
    args = parser.parse_args()

    # Emit early to show agent has started
    emit_status("DeepAgents Research Agent (Orchestrator + Subagents) starting...")

    # Check for API keys
    if not os.environ.get("OPENAI_API_KEY"):
        emit_error("OPENAI_API_KEY not set")
        sys.exit(1)

    if not os.environ.get("TAVILY_API_KEY"):
        emit_error("TAVILY_API_KEY not set")
        sys.exit(1)

    # Get workspace directory (defaults to current directory)
    workspace = os.environ.get("AGENT_WORKSPACE", os.getcwd())
    workspace = os.path.abspath(workspace)

    if not os.path.isdir(workspace):
        emit_error(f"Workspace directory does not exist: {workspace}")
        sys.exit(1)

    # Get prompt
    prompt = None
    if args.prompt:
        prompt = args.prompt
        emit_status("Using prompt from --prompt argument")
    else:
        prompt_file = os.path.join(workspace, "prompt.txt")
        if os.path.isfile(prompt_file):
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    prompt = f.read().strip()
                emit_status("Analyzing research request...")
            except Exception as e:
                emit_error(f"Failed to read prompt file: {e}")
                sys.exit(1)
        else:
            emit_error(
                f"No prompt provided. Either use --prompt or create {prompt_file}"
            )
            sys.exit(1)

    if not prompt:
        emit_error("Empty prompt provided")
        sys.exit(1)

    # Try to read conversation history
    history = None
    history_file = os.path.join(workspace, "history.txt")
    if os.path.isfile(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_content = f.read().strip()
                if history_content:
                    try:
                        history = json.loads(history_content)
                    except json.JSONDecodeError:
                        emit_warning(f"Could not parse {history_file} as JSON, ignoring history")
        except Exception as e:
            emit_warning(f"Failed to read history file: {e}")

    # Run the agent
    asyncio.run(run_agent(prompt, workspace, history))

if __name__ == "__main__":
    main()
