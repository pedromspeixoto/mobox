"""Shared types for sandbox implementations."""
from dataclasses import dataclass


@dataclass
class AgentEvent:
    """Event emitted by agent execution."""
    type: str
    data: dict
