#!/usr/bin/env python3
"""Entry point for research agent using AgentDefinition for subagents.

This multi-agent research system coordinates specialized agents to:
1. Research topics via web search
2. Analyze data and generate visualizations
3. Generate PDF or PPTX reports
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    HookMatcher,
)

from shared.emitter import (
    emit,
    emit_status,
    emit_error,
    emit_done,
    emit_warning,
)
from shared.load_prompt import load_prompt
from shared.utils.claude_parser import process_assistant_message, process_result_message
from utils.file_manager import ensure_directories
from utils.subagent_tracker import SubagentTracker

# Paths to prompt files
PROMPTS_DIR = Path(__file__).parent / "prompts"


async def run_agent(prompt: str, workspace: str, history: list = None) -> None:
    """Execute the research agent with the given prompt.

    Args:
        prompt: The user prompt to send to the agent
        workspace: Working directory for file operations
        history: Optional list of previous conversation messages
    """
    # Ensure workspace directories exist
    ensure_directories(workspace)

    # Load prompts for all agents (inject workspace path)
    lead_agent_prompt = load_prompt("lead_agent.txt", workspace, PROMPTS_DIR)
    researcher_prompt = load_prompt("researcher.txt", workspace, PROMPTS_DIR)
    data_analyst_prompt = load_prompt("data_analyst.txt", workspace, PROMPTS_DIR)
    report_writer_prompt = load_prompt("report_writer.txt", workspace, PROMPTS_DIR)

    # Initialize subagent tracker
    tracker = SubagentTracker(workspace=workspace)

    # Define specialized subagents using AgentDefinition
    agents = {
        "researcher": AgentDefinition(
            description=(
                "Use this agent to gather research on a specific subtopic. "
                "Uses 5-7 WebSearch calls to find QUANTITATIVE DATA (numbers, statistics, percentages). "
                f"Writes findings to {workspace}/files/research_notes/{{topic}}.md with 10-15 statistics minimum. "
                "Spawn 2 researchers in parallel for different subtopics."
            ),
            tools=["WebSearch", "Write"],
            prompt=researcher_prompt,
            model="haiku"
        ),
        "data-analyst": AgentDefinition(
            description=(
                f"Use AFTER all researchers complete. Reads {workspace}/files/research_notes/, extracts data, "
                f"generates exactly 3 charts to {workspace}/files/charts/, writes summary to {workspace}/files/data/data_summary.md. "
                "Charts: 1 trend/growth, 1 comparison, 1 distribution."
            ),
            tools=["Glob", "Read", "Bash", "Write"],
            prompt=data_analyst_prompt,
            model="haiku"
        ),
        "report-writer": AgentDefinition(
            description=(
                f"Use AFTER data-analyst completes. Reads {workspace}/files/research_notes/, {workspace}/files/data/, "
                f"{workspace}/files/charts/, creates PDF/PPTX/text output in {workspace}/files/reports/. "
                "Uses pdf or pptx skill for document generation."
            ),
            tools=["Skill", "Write", "Glob", "Read", "Bash"],
            prompt=report_writer_prompt,
            model="haiku"
        )
    }

    # Set up hooks for tracking subagent tool calls
    hooks = {
        'PreToolUse': [
            HookMatcher(
                matcher=None,  # Match all tools
                hooks=[tracker.pre_tool_use_hook]
            )
        ],
        'PostToolUse': [
            HookMatcher(
                matcher=None,  # Match all tools
                hooks=[tracker.post_tool_use_hook]
            )
        ]
    }

    # Configure the main agent options
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        setting_sources=["project"],  # Load skills from project .claude directory
        system_prompt=lead_agent_prompt,
        allowed_tools=["Task", "TodoWrite"],
        agents=agents,
        hooks=hooks,
        model="haiku",
        cwd=workspace,
    )

    emit("start", {"prompt": prompt[:100], "has_history": history is not None})

    try:
        async with ClaudeSDKClient(options=options) as client:
            # Send the prompt to the agent
            await client.query(prompt=prompt)

            # Process the response stream
            async for msg in client.receive_response():
                msg_type = type(msg).__name__

                if msg_type == "AssistantMessage":
                    tracker.set_current_context(getattr(msg, "parent_tool_use_id", None))
                    process_assistant_message(
                        msg,
                        emit,
                        on_task=lambda tid, st, d, p: tracker.register_subagent_spawn(
                            tool_use_id=tid, subagent_type=st, description=d, prompt=p
                        ),
                    )
                elif msg_type == "ResultMessage":
                    process_result_message(msg, emit)

    except Exception as e:
        emit_error(f"Agent error: {str(e)}")
        raise
    finally:
        tracker.close()

    emit_done()


def main():
    """Main entry point for the research agent."""
    # Load .env file if available (for local development)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, skip (production/container)

    import argparse
    parser = argparse.ArgumentParser(description="Run Claude Research Agent")
    parser.add_argument(
        "--prompt",
        type=str,
        help="Prompt to send to the agent (overrides prompt.txt)"
    )
    args = parser.parse_args()

    # Emit early to show agent has started
    emit_status("Claude Research Agent starting...")

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        emit_error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Get workspace directory (defaults to current directory for local development)
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
