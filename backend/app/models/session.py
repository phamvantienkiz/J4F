from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
import datetime

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    session_id: str = Field(primary_key=True)
    history: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    slots: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    current_intent: Optional[str] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
