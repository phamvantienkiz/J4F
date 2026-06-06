import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
import uuid

from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.services.auth_service import get_user_preference
from backend.app.schemas.chat import MessageResponse, ConversationResponse
from ai.agent import agent_graph
from ai.state import Requirements, UserPreference as AgentUserPreference

async def get_or_create_conversation(
    db: AsyncSession, user_id: str, conversation_id: Optional[str] = None, title: Optional[str] = None
) -> Conversation:
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalars().first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return conversation

    # Create new conversation
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title or "Cuộc hội thoại mới"
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation

async def get_conversations(db: AsyncSession, user_id: str) -> List[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())

async def get_conversation_history(db: AsyncSession, conversation_id: str) -> List[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())

async def send_chat_message(
    db: AsyncSession, user_id: str, conversation_id: str, message_content: str
) -> Dict[str, Any]:
    # 1. Fetch conversation and user preferences
    conversation = await get_or_create_conversation(db, user_id, conversation_id)
    pref = await get_user_preference(db, user_id)
    
    # Save the user's incoming message to SQLite immediately
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        sender="user",
        content=message_content,
        created_at=datetime.utcnow()
    )
    db.add(user_msg)
    await db.flush()

    # 2. Prepare LangGraph State invocation config
    config = {"configurable": {"thread_id": conversation.id}}
    
    # Fetch current state of this thread
    state = agent_graph.get_state(config)
    
    # Prepare agent pref format
    agent_pref = AgentUserPreference(
        preferred_market=pref.preferred_market,
        target_margin=pref.target_margin,
        max_shipping_days=pref.max_shipping_days,
        fulfillment_priority=pref.fulfillment_priority
    )

    if not state.values:
        # Initial invocation
        initial_state = {
            "thread_id": conversation.id,
            "user_preferences": agent_pref,
            "conversation_history": [{"sender": "user", "content": message_content}],
            "requirements": Requirements(),
            "candidates": [],
            "calculated_options": [],
            "ranking_results": [],
            "last_missing_fields": [],
            "order_draft": None,
            "order_status": None
        }
        output = agent_graph.invoke(initial_state, config)
    else:
        # Sub-sequential turn
        current_values = state.values
        history = list(current_values.get("conversation_history", []))
        history.append({"sender": "user", "content": message_content})

        # Smart order draft trigger
        order_draft = current_values.get("order_draft")
        ranking_results = current_values.get("ranking_results", [])
        
        # Check if the user is choosing a factory option
        user_msg_lower = message_content.lower()
        if ranking_results and any(kw in user_msg_lower for kw in ["chốt", "chọn", "đặt xưởng", "đặt option", "chốt xưởng", "choose", "select"]):
            selected_factory = None
            for opt in ranking_results:
                if opt.factory_name.lower() in user_msg_lower or opt.option_id.lower() in user_msg_lower:
                    selected_factory = opt
                    break
            
            # Default fallback to top 1 if user just says "chốt" or "chọn" general
            if not selected_factory:
                # E.g. "chốt xưởng số 1" or "chọn xưởng đầu tiên"
                if "1" in user_msg_lower or "đầu" in user_msg_lower:
                    selected_factory = ranking_results[0]
                elif "2" in user_msg_lower and len(ranking_results) > 1:
                    selected_factory = ranking_results[1]
                elif "3" in user_msg_lower and len(ranking_results) > 2:
                    selected_factory = ranking_results[2]
                else:
                    selected_factory = ranking_results[0]
            
            if selected_factory:
                product_name = current_values.get("candidates", [{}])[0].get("product_name", "Classic Unisex T-Shirt")
                sku = "BP-UNISEX-TSHIRT-BLK-L"
                if "hoodie" in product_name.lower():
                    sku = "BP-FLEECE-HOODIE-BLK-L"
                elif "mug" in product_name.lower():
                    sku = "BP-CERAMIC-MUG-WHT-STD"
                
                order_draft = {
                    "sku": sku,
                    "quantity": 1,
                    "shipping_name": "John Doe",
                    "shipping_address_line1": "123 Main St",
                    "shipping_city": "San Jose",
                    "shipping_state": "CA",
                    "shipping_zip": "95112",
                    "shipping_country": "US",
                    "selected_option_id": selected_factory.option_id
                }

        update_state = {
            "conversation_history": history,
            "user_preferences": agent_pref
        }
        if order_draft:
            update_state["order_draft"] = order_draft

        # Invoke agent workflow
        output = agent_graph.invoke(update_state, config)

    # 3. Find the new messages generated by the assistant during this run
    new_history = output.get("conversation_history", [])
    db_history = await get_conversation_history(db, conversation.id)
    
    # We want to identify the assistant's new response
    assistant_responses = [m for m in new_history if m["sender"] == "assistant"]
    
    # Store the latest assistant response in SQLite DB
    if assistant_responses:
        latest_assistant = assistant_responses[-1]
        
        # Meta info
        meta_dict = latest_assistant.get("metadata", {})
        
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            sender="assistant",
            content=latest_assistant["content"],
            metadata_json=json.dumps(meta_dict) if meta_dict else None,
            created_at=datetime.utcnow()
        )
        db.add(assistant_msg)
        
    # Auto rename conversation title if it was default
    if conversation.title == "Cuộc hội thoại mới" and len(message_content) < 50:
        conversation.title = message_content
    elif conversation.title == "Cuộc hội thoại mới":
        conversation.title = message_content[:47] + "..."

    conversation.updated_at = datetime.utcnow()
    db.add(conversation)
    
    await db.commit()
    await db.refresh(conversation)

    # Reload all messages for clean response
    db_messages = await get_conversation_history(db, conversation.id)
    
    # Map messages to Pydantic responses
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
