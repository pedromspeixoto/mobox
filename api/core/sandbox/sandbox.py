"""Sandbox factory and implementations for running agents.

Two backends:
- modal: Runs agents in Modal sandboxes (isolated containers)
- subprocess: Runs agents locally as subprocess (no Modal/Docker)
"""
from enum import Enum
from typing import AsyncIterator, Protocol

from core.config import settings
from core.logging import get_logger
from core.sandbox.types import AgentEvent
from core.sandbox.subprocess import SubprocessClient
from core.sandbox.modal import ModalClient

logger = get_logger(__name__)


class SandboxType(Enum):
    SUBPROCESS = "subprocess"
    MODAL = "modal"


class SandboxClient(Protocol):
    """Protocol for sandbox implementations."""

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
        """Run an agent and stream its output events."""
        ...


def get_sandbox_client() -> SandboxClient:
    """Factory: return the configured sandbox implementation.

    Uses SANDBOX_BACKEND env var: SandboxType.MODAL (default) or SandboxType.SUBPROCESS.
    """
    backend = settings.SANDBOX_BACKEND
    if backend == SandboxType.MODAL.value:
        return ModalClient()
    else:
        return SubprocessClient()
