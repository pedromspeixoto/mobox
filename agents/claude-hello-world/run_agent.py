#!/usr/bin/env python3
"""Hello World Agent - Entry point for Claude Agent SDK execution.

This script runs inside the Modal sandbox and streams output back
to the Mobox API via stdout as JSON events.

Usage:
    python run_agent.py                          # Read from prompt.txt and history.txt
    python run_agent.py --prompt "Your prompt"   # Override with direct prompt
"""
import asyncio
import argparse
import json
import sys
import os

from shared.emitter import (
    emit,
    emit_status,
    emit_error,
    emit_warning,
    emit_thinking,
    emit_done,
)
from shared.utils.claude_parser import process_assistant_message, process_result_message
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, ResultMessage


async def run_agent(prompt: str, workspace: str, history: list = None) -> None:
    """Execute the Claude Agent SDK with the given prompt and optional history.

    Args:
        prompt: The user prompt to send to the agent
        workspace: Working directory for file operations
        history: Optional list of previous conversation messages
    """

    options = ClaudeAgentOptions(
        system_prompt="""You are a helpful assistant running in a sandboxed environment.
You can read and write files, and execute bash commands.
Be concise and helpful in your responses.""",
        allowed_tools=["Read", "Write", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",
        max_turns=10,
        cwd=workspace,
    )

    emit("start", {"prompt": prompt[:100], "has_history": history is not None})

    # Emit thinking events for testing (simulates agent reasoning)
    emit_thinking("Hmm, let me think about this carefully...\n")
    emit_thinking("The user is asking for help. I should consider the best approach.\n")
    emit_thinking("I'll provide a clear and concise response.")

    try:
        async with ClaudeSDKClient(options=options) as client:
            # TODO: If SDK supports history, pass it here
            # For now, we just send the current prompt
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    process_assistant_message(message, emit)
                elif isinstance(message, ResultMessage):
                    process_result_message(message, emit)

    except Exception as e:
        emit_error(str(e))
        raise

    emit_done()


def main():
    # Load .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, skip (production/container)

    parser = argparse.ArgumentParser(description="Run Hello World Agent")
    parser.add_argument("--prompt", type=str, help="Prompt to send to the agent (overrides prompt.txt)")
    args = parser.parse_args()

    # Emit early to show agent has started
    emit_status("Agent started, checking configuration...")

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        emit_error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Get workspace directory (defaults to current directory for local development)
    workspace = os.environ.get("AGENT_WORKSPACE", os.getcwd())

    # Resolve relative paths and ensure directory exists
    workspace = os.path.abspath(workspace)
    if not os.path.isdir(workspace):
        emit_error(f"Workspace directory does not exist: {workspace}")
        sys.exit(1)

    # Get prompt: either from --prompt argument or from prompt.txt
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
                emit_status("Analyzing your question...")
            except Exception as e:
                emit_error(f"Failed to read prompt file: {e}")
                sys.exit(1)
        else:
            emit_error(f"No prompt provided. Either use --prompt or create {prompt_file}")
            sys.exit(1)

    if not prompt:
        emit_error("Empty prompt provided")
        sys.exit(1)

    # Try to read conversation history (optional)
    history = None
    history_file = os.path.join(workspace, "history.txt")
    if os.path.isfile(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_content = f.read().strip()
                if history_content:
                    # Try to parse as JSON
                    try:
                        history = json.loads(history_content)
                    except json.JSONDecodeError:
                        emit_warning(f"Could not parse {history_file} as JSON, ignoring history")
        except Exception as e:
            emit_warning(f"Failed to read history file: {e}")

    asyncio.run(run_agent(prompt, workspace, history))


if __name__ == "__main__":
    main()
