"""API routes for agent management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.agents import load_agent_config, list_agents
from core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class AgentResponse(BaseModel):
    """Response model for agent info"""
    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    framework: str = Field(default="claude", description="Agent framework (claude, deepagents, etc.)")


@router.get("/", response_model=list[AgentResponse])
async def get_agents():
    """Get list of available agents"""
    logger.info("Fetching available agents")
    agents = list_agents()
    return [
        AgentResponse(id=a.id, name=a.name, description=a.description, framework=a.framework)
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get a specific agent by ID"""
    logger.info(f"Fetching agent: {agent_id}")
    
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    return AgentResponse(id=config.id, name=config.name, description=config.description, framework=config.framework)
