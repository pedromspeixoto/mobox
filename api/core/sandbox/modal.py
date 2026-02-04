"""Modal sandbox client for running agents in isolated containers.

Based on Modal Sandboxes: https://modal.com/docs/guide/sandboxes

Lifecycle:
- timeout: Maximum lifetime of sandbox (default 5 min, max 24 hours)
- idle_timeout: Auto-terminate after period of inactivity
"""
import asyncio
import json
import os
from typing import AsyncIterator

import modal

from core.config import settings
from core.logging import get_logger
from core.sandbox.types import AgentEvent

logger = get_logger(__name__)

# Default timeouts
DEFAULT_TIMEOUT = 10 * 60  # 10 minutes max lifetime
DEFAULT_IDLE_TIMEOUT = 2 * 60  # 2 minutes idle before termination


class ModalClient:
    """Client for managing Modal sandboxes."""
    
    def __init__(self):
        self.app = None
        self._initialized = False

    def _read_process_stdout_sync(self, process, queue: asyncio.Queue, loop):
        """Synchronous helper to read process stdout (runs in thread pool).

        This method runs in a separate thread to avoid blocking the async event loop.
        It reads from process.stdout (blocking I/O) and pushes events to the queue.
        """
        try:
            for chunk in process.stdout:
                # process.stdout may return chunks with multiple lines
                # Split by newlines and process each line separately
                for line in chunk.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                        logger.info(f"Parsed JSON event: type={event.get('type', 'unknown')}")
                        # Use asyncio.run_coroutine_threadsafe to put into the queue from another thread
                        asyncio.run_coroutine_threadsafe(
                            queue.put(AgentEvent(
                                type=event.get("type", "unknown"),
                                data=event.get("data", {}),
                            )),
                            loop
                        )
                    except json.JSONDecodeError as e:
                        # Non-JSON output, emit as raw text
                        logger.warning(f"JSON parse failed for line: {line[:100]}... Error: {e}")
                        asyncio.run_coroutine_threadsafe(
                            queue.put(AgentEvent(type="raw", data={"content": line})),
                            loop
                        )

        except Exception as e:
            logger.error(f"Error streaming process output: {e}")
            asyncio.run_coroutine_threadsafe(
                queue.put(AgentEvent(type="error", data={"message": str(e)})),
                loop
            )
        finally:
            # Wait for process completion and check return code
            try:
                process.wait()  # Must call wait() before accessing returncode
                returncode = process.returncode
                if returncode is not None and returncode != 0:
                    asyncio.run_coroutine_threadsafe(
                        queue.put(AgentEvent(type="exit", data={"returncode": returncode})),
                        loop
                    )
            except Exception as e:
                logger.error(f"Error waiting for process: {e}")

            # Signal completion
            asyncio.run_coroutine_threadsafe(
                queue.put(None),  # Sentinel value to signal end of stream
                loop
            )

    async def initialize(self) -> None:
        """Initialize Modal app connection."""
        if self._initialized:
            return

        # Set Modal credentials from settings if available
        if settings.MODAL_TOKEN_ID and settings.MODAL_TOKEN_SECRET:
            os.environ["MODAL_TOKEN_ID"] = settings.MODAL_TOKEN_ID
            os.environ["MODAL_TOKEN_SECRET"] = settings.MODAL_TOKEN_SECRET
            logger.info("Set Modal credentials from settings")

        # Look up or create the Modal app
        self.app = await modal.App.lookup.aio("mobox-agents", create_if_missing=True)
        self._initialized = True
        logger.info("Modal client initialized")
    
    async def create_sandbox(
        self,
        session_id: str,
        image_url: str,
        agent_id: str,
        prompt: str,
        env_vars: dict[str, str],
        timeout: int = DEFAULT_TIMEOUT,
        idle_timeout: int = DEFAULT_IDLE_TIMEOUT,
        history: str | None = None,
    ) -> modal.Sandbox:
        """Create or reuse a sandbox for running an agent.

        Tries to reuse an existing sandbox with the session_id as the name.
        If it doesn't exist or has stopped, creates a new one.

        Args:
            session_id: Session identifier (used as sandbox name)
            image_url: Docker registry URL for the agent image
            agent_id: Agent identifier (used for naming/tagging)
            prompt: The prompt to send to the agent
            env_vars: Environment variables to pass to the sandbox
            timeout: Max lifetime in seconds (default 10 min)
            idle_timeout: Idle timeout in seconds (default 2 min)
            history: Optional conversation history (JSON string)

        Returns:
            Modal Sandbox instance with files written
        """
        await self.initialize()

        # Try to reuse existing sandbox by name
        sandbox = None
        need_new_sandbox = False

        try:
            sandbox = await modal.Sandbox.from_name.aio(
                "mobox-agents",
                session_id       # sandbox name
            )

            # Check if sandbox is still running (poll returns None if running, exit code if finished)
            exit_code = await sandbox.poll.aio()
            if exit_code is not None:
                logger.info(f"Found sandbox for session {session_id} but it has finished (exit={exit_code}), creating new one")
                need_new_sandbox = True
            else:
                logger.info(f"Reusing existing sandbox for session {session_id}: {sandbox.object_id}")

        except Exception as e:
            # Sandbox doesn't exist
            logger.info(f"Sandbox not found for session {session_id} (reason: {str(e)}), creating new one")
            need_new_sandbox = True

        # Create new sandbox if needed
        if need_new_sandbox:
            # Use prebuilt image from registry
            image = modal.Image.from_registry(image_url)

            # Create secret from env vars
            secret = modal.Secret.from_dict(env_vars) if env_vars else None
            secrets = [secret] if secret else []

            sandbox = await modal.Sandbox.create.aio(
                name=session_id,  # Use session_id as sandbox name
                app=self.app,
                image=image,
                secrets=secrets,
                timeout=timeout,
                idle_timeout=idle_timeout,
                workdir="/workspace",
                env={
                    "PYTHONUNBUFFERED": "1",
                    "AGENT_ID": agent_id,
                },
            )

            # Tag for tracking
            await sandbox.set_tags.aio({
                "agent_id": agent_id,
                "session_id": session_id,
                "type": "mobox-agent",
            })

            logger.info(f"Created new sandbox for session {session_id}: {sandbox.object_id}")

        # Write prompt to file (always write, even for reused sandboxes)
        prompt_file = await sandbox.open.aio("/workspace/prompt.txt", "w")
        await prompt_file.write.aio(prompt)
        await prompt_file.close.aio()
        logger.debug(f"Wrote prompt to /workspace/prompt.txt ({len(prompt)} chars)")

        # Write history file if provided
        if history:
            history_file = await sandbox.open.aio("/workspace/history.txt", "w")
            await history_file.write.aio(history)
            await history_file.close.aio()
            logger.debug(f"Wrote history to /workspace/history.txt ({len(history)} chars)")

        return sandbox
    
    async def stream_agent_output(
        self,
        sandbox: modal.Sandbox,
        command: list[str],
    ) -> AsyncIterator[AgentEvent]:
        """Stream output events from an agent sandbox.

        Starts the agent process, then yields AgentEvent objects parsed from stdout.
        Agent outputs JSON lines: {"type": "...", "data": {...}}

        Uses a queue-based approach to avoid blocking the async event loop
        with synchronous I/O operations.

        Args:
            sandbox: The Modal sandbox instance
            command: Command to execute (e.g., ["python", "/app/run_agent.py"])
        """
        logger.info(f"Starting stream_agent_output with command: {' '.join(command)}")

        # Start the agent process
        # Files (prompt.txt, history.txt) are already written to /workspace
        process = await sandbox.exec.aio(*command)
        logger.info(f"Executed sandbox.exec.aio(), got process: {type(process)}")

        queue: asyncio.Queue = asyncio.Queue()

        # Start reading stdout in a separate thread
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, self._read_process_stdout_sync, process, queue, loop)

        # Yield events from the queue
        logger.info("Starting to read events from queue...")
        event_count = 0
        while True:
            event = await queue.get()
            if event is None:  # Sentinel value indicating end of stream
                logger.info(f"Received sentinel value, ending stream after {event_count} events")
                break
            event_count += 1
            logger.info(f"Yielding event #{event_count}: type={event.type}")
            yield event
    
    async def run_agent(
        self,
        session_id: str,
        image_url: str,
        agent_id: str,
        prompt: str,
        env_vars: dict[str, str],
        command: list[str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        idle_timeout: int = DEFAULT_IDLE_TIMEOUT,
        history: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Run an agent and stream its output.

        This is the main method to execute an agent in a sandbox.
        Creates sandbox, writes files, streams output, and cleans up.

        Args:
            session_id: Session identifier
            image_url: Docker registry URL for the agent image
            agent_id: Agent identifier
            prompt: The prompt to send to the agent
            env_vars: Environment variables (API keys, etc.)
            command: Command to execute (defaults to ["python", "/app/run_agent.py"])
            timeout: Max lifetime in seconds
            idle_timeout: Idle timeout in seconds
            history: Optional conversation history (JSON string)
        """
        logger.info(f"run_agent called for session {session_id}, agent {agent_id}")
        if command is None:
            command = ["python", "/app/run_agent.py"]

        sandbox = None
        try:
            # Step 1: Create sandbox
            logger.info("Yielding 'Creating sandbox...' status event")
            yield AgentEvent(type="status", data={"message": "Creating sandbox..."})

            sandbox = await self.create_sandbox(
                session_id=session_id,
                image_url=image_url,
                agent_id=agent_id,
                prompt=prompt,
                env_vars=env_vars,
                timeout=timeout,
                idle_timeout=idle_timeout,
                history=history,
            )

            # Step 2: Files are written in create_sandbox
            yield AgentEvent(type="status", data={"message": "Wrote prompt.txt and history.txt to sandbox"})

            # Step 3: Start agent and stream output
            yield AgentEvent(type="status", data={"message": "Starting agent..."})

            async for event in self.stream_agent_output(sandbox, command):
                yield event

                # Stop on done or error
                if event.type in ("done", "error"):
                    break

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Agent execution error: {error_msg}", exc_info=True)

            # Format Modal-specific errors for better UX
            if "Image build" in error_msg:
                formatted_msg = "Failed to build agent image. Please check agent configuration."
            elif "Token missing" in error_msg or "authenticate" in error_msg:
                formatted_msg = "Modal authentication failed. Please check your credentials."
            elif "not found" in error_msg.lower():
                formatted_msg = "Agent image not found. Please check the image URL."
            else:
                formatted_msg = f"Agent execution failed: {error_msg}"

            yield AgentEvent(type="error", data={"message": formatted_msg, "details": error_msg})

        # NOTE: We don't terminate the sandbox here to allow reuse for subsequent requests.
        # Sandboxes will be automatically cleaned up after idle_timeout (default 2 minutes)
        # or timeout (default 10 minutes) expires.
    
    async def terminate_sandbox(self, sandbox_id: str) -> bool:
        """Terminate a sandbox by ID.

        Returns True if terminated successfully.
        """
        try:
            sandbox = await modal.Sandbox.from_id.aio(sandbox_id)
            await sandbox.terminate.aio()
            logger.info(f"Terminated sandbox: {sandbox_id}")
            return True
        except Exception as e:
            logger.error(f"Error terminating sandbox {sandbox_id}: {e}")
            return False
