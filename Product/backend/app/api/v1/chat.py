from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from backend.app.api.deps import get_db, get_current_user
from backend.app.models.user import User
from backend.app.schemas.chat import (
    ConversationResponse, MessageResponse, MessageCreate, ChatHistoryResponse
)
from backend.app.services import chat_service

router = APIRouter()

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await chat_service.get_conversations(db, current_user.id)

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    title: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await chat_service.get_or_create_conversation(db, current_user.id, title=title)

@router.get("/conversations/{conversation_id}/history", response_model=ChatHistoryResponse)
async def get_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conversation = await chat_service.get_or_create_conversation(db, current_user.id, conversation_id)
    db_messages = await chat_service.get_conversation_history(db, conversation_id)
    
    # Map messages to Pydantic schema
    import json
    response_messages = []
    for msg in db_messages:
        meta = None
        if msg.metadata_json:
            try:
                meta = json.loads(msg.metadata_json)
            except Exception:
                pass
        response_messages.append(MessageResponse(
            id=msg.id,
            sender=msg.sender,
            content=msg.content,
            metadata=meta,
            created_at=msg.created_at
        ))
        
    return {
        "conversation": ConversationResponse.model_validate(conversation),
        "messages": response_messages
    }

@router.post("/conversations/{conversation_id}/message", response_model=ChatHistoryResponse)
async def send_message(
    conversation_id: str,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # This will call LangGraph agent, calculate details, generate response and save to SQLite
    res = await chat_service.send_chat_message(
        db, current_user.id, conversation_id, message_in.content
    )
    return res
