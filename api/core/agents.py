"""Agent configuration and loading."""
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
import yaml

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Base path for agents
AGENTS_DIR = Path(__file__).parent.parent.parent / "agents"

# Allowed env vars that can be passed to sandboxes (whitelist for security)
ALLOWED_ENV_VARS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "HUGGINGFACE_API_KEY",
    "GROQ_API_KEY",
    "TAVILY_API_KEY",
    # Add more as needed
}


class AgentConfig(BaseModel):
    """Agent configuration - metadata for the API"""
    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="Agent description")
    path: str = Field(..., description="Path to agent directory (relative to agents/)")

    # Agent framework (claude, openai, gemini, etc.)
    framework: str = Field(default="claude", description="Agent framework for event formatting")

    # Docker image for sandbox execution
    image: Optional[str] = Field(None, description="Docker registry URL for prebuilt image")

    # Command to run the agent in the sandbox
    command: list[str] = Field(
        default_factory=lambda: ["python", "/app/run_agent.py"],
        description="Command to execute in the sandbox"
    )

    # Environment variables the agent needs (names only, values come from server env)
    env_vars: list[str] = Field(default_factory=list, description="Required env var names")

    # Optional sandbox settings
    timeout: int = Field(default=600, description="Max sandbox lifetime in seconds")
    idle_timeout: int = Field(default=120, description="Idle timeout before termination")


def load_agent_config(agent_id: str) -> AgentConfig | None:
    """Load agent configuration from YAML file."""
    config_path = AGENTS_DIR / agent_id / "agent.yaml"

    if not config_path.exists():
        logger.warning(f"Agent config not found: {config_path}")
        return None

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)

        # Support both 'command' and 'entrypoint' field names
        command = data.get("command") or data.get("entrypoint") or ["python", "/app/run_agent.py"]

        return AgentConfig(
            id=agent_id,
            name=data.get("name", agent_id),
            description=data.get("description", ""),
            path=agent_id,
            framework=data.get("framework", "claude"),
            image=data.get("image"),
            command=command,
            env_vars=data.get("env_vars", []),
            timeout=data.get("timeout", 600),
            idle_timeout=data.get("idle_timeout", 120),
        )
    except Exception as e:
        logger.error(f"Error loading agent config {agent_id}: {e}")
        return None


def get_agent_env_vars(agent_config: AgentConfig) -> dict[str, str]:
    """Get environment variables for an agent from settings.

    Only returns env vars that:
    1. Are in the agent's env_vars list
    2. Are in the ALLOWED_ENV_VARS whitelist
    3. Are set in settings (loaded from .env)

    Returns:
        Dict of env var name -> value
    """
    env = {}

    for var_name in agent_config.env_vars:
        # Security: only allow whitelisted env vars
        if var_name not in ALLOWED_ENV_VARS:
            logger.warning(f"Agent {agent_config.id} requested non-whitelisted env var: {var_name}")
            continue

        # Always use settings (single source of truth from .env)
        value = getattr(settings, var_name, None)
        if value:
            env[var_name] = value
            logger.info(f"Loaded {var_name} for agent {agent_config.id}")
        else:
            logger.warning(f"Agent {agent_config.id} requires {var_name} but it's not set in settings")

    return env


def list_agents() -> list[AgentConfig]:
    """List all available agents."""
    agents = []
    
    if not AGENTS_DIR.exists():
        logger.warning(f"Agents directory not found: {AGENTS_DIR}")
        return agents
    
    for agent_dir in AGENTS_DIR.iterdir():
        if agent_dir.is_dir() and not agent_dir.name.startswith("."):
            config = load_agent_config(agent_dir.name)
            if config:
                agents.append(config)
    
    return sorted(agents, key=lambda a: a.name)


def get_agent_path(agent_id: str) -> Path | None:
    """Get the full path to an agent's directory."""
    agent_path = AGENTS_DIR / agent_id
    
    if not agent_path.exists():
        return None
    
    return agent_path
