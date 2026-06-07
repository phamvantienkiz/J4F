from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
