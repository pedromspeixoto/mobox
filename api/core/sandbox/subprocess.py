"""Local subprocess sandbox - runs agents with uv run"""
import asyncio
import json
import os
from typing import AsyncIterator

from core.agents import AGENTS_DIR, load_agent_config, get_agent_env_vars
from core.logging import get_logger

from core.sandbox.types import AgentEvent

logger = get_logger(__name__)


async def _read_process_stdout_async(process, queue: asyncio.Queue) -> None:
    """Read process stdout, push AgentEvent to queue."""
    try:
        if process.stdout:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line = line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    await queue.put(AgentEvent(type=event.get("type", "unknown"), data=event.get("data", {})))
                except json.JSONDecodeError:
                    await queue.put(AgentEvent(type="raw", data={"content": line}))
    except Exception as e:
        logger.error(f"Error reading agent stdout: {e}")
        await queue.put(AgentEvent(type="error", data={"message": str(e)}))
    finally:
        await queue.put(None)


async def _drain_stderr_async(process, stderr_lines: list[str] | None = None) -> None:
    """Drain stderr to prevent pipe buffer from filling and blocking the subprocess.

    Agents (especially Claude SDK) may log to stderr. If stderr is piped but never
    read, the buffer fills and the subprocess blocks on write. This task drains
    stderr so the agent can continue; we log at debug level for troubleshooting.

    If stderr_lines is provided, all stderr output is appended for later use
    (e.g. to surface subprocess crash errors to the user).
    """
    try:
        if process.stderr:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    if stderr_lines is not None:
                        stderr_lines.append(text)
                    logger.debug("Agent stderr: %s", text)
    except Exception as e:
        logger.debug("Stopped draining agent stderr: %s", e)

class SubprocessClient:
    """Local subprocess sandbox - runs agents with uv run (no Modal/Docker)."""

    async def run_agent(
        self,
        session_id: str,
        image_url: str,
        agent_id: str,
        prompt: str,
        env_vars: dict[str, str],
        command: list[str] | None = None,
        timeout: int = 600,
        idle_timeout: int = 120,
        history: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Run agent locally as subprocess. Ignores session_id, image_url, command, timeouts."""
        agent_config = load_agent_config(agent_id)
        if not agent_config:
            yield AgentEvent(type="error", data={"message": f"Agent '{agent_id}' not found"})
            return

        agent_path = AGENTS_DIR / agent_id
        if not agent_path.exists():
            yield AgentEvent(type="error", data={"message": f"Agent path not found: {agent_path}"})
            return

        # Set env variables for agent execution in subprocess
        resolved_env = os.environ.copy()
        resolved_env.update(get_agent_env_vars(agent_config))

        # Create workspace directory for agent execution
        workspace_dir = agent_path / "workspace" / session_id
        workspace_dir.mkdir(parents=True, exist_ok=True)

        (workspace_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        if history:
            (workspace_dir / "history.txt").write_text(history, encoding="utf-8")
        resolved_env["AGENT_WORKSPACE"] = str(workspace_dir)

        yield AgentEvent(type="status", data={"message": "Starting agent locally..."})

        # Sandbox command is ignored in subprocess sandbox (defaults to uv run python run_agent.py)
        cmd = ["uv", "run", "python", "run_agent.py"]

        logger.info(f"Executing agent command: {' '.join(cmd)}")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(agent_path),
                env=resolved_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            yield AgentEvent(
                type="error",
                data={"message": f"Could not execute agent command: {cmd}"},
            )
            return

        queue: asyncio.Queue = asyncio.Queue()
        stderr_lines: list[str] = []
        read_task = asyncio.create_task(_read_process_stdout_async(process, queue))
        stderr_task = asyncio.create_task(_drain_stderr_async(process, stderr_lines))

        cancelled = False
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        except asyncio.CancelledError:
            cancelled = True
            pass
        finally:
            read_task.cancel()
            stderr_task.cancel()
            try:
                await read_task
            except asyncio.CancelledError:
                pass
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass

        # Check process exit status 
        if cancelled and process.returncode is None:
            process.terminate()
        await process.wait()
        if process.returncode and process.returncode != 0:
            stderr_text = "\n".join(stderr_lines).strip() if stderr_lines else ""
            error_msg = (
                f"Agent exited with code {process.returncode}"
                + (f": {stderr_text}" if stderr_text else "")
            )
            logger.error("Agent subprocess failed: %s", error_msg)
            yield AgentEvent(type="error", data={"message": error_msg, "details": stderr_text})