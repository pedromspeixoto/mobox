"""Session request/response schemas"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    """Request model for creating a new chat session"""
    agent_id: str = Field(..., description="Agent ID for this chat")
    agent_name: str = Field(..., description="Agent display name")
    title: Optional[str] = Field(None, description="Optional session title")


class ChatSessionResponse(BaseModel):
    """Response model for chat session"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Session UUID")
    title: Optional[str] = Field(None, description="Session title")
    agent_id: str = Field(default="hello-world", description="Agent ID used for this chat")
    agent_name: Optional[str] = Field(None, description="Agent display name")
    created_at: str = Field(..., description="ISO format creation timestamp")
    updated_at: str = Field(..., description="ISO format last update timestamp")
    sdk_session_id: Optional[str] = Field(None, description="Vendor SDK session ID (for resuming conversations)")
