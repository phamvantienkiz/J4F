from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.agent.engine import AgentEngine
import uuid
import json

router = APIRouter()
agent_engine = AgentEngine()

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, alias="session_id")
    message: str
    history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    class Config:
        populate_by_name = True

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id
    if not session_id:
        session_id = f"sess-{uuid.uuid4().hex[:8]}"

    try:
        # Sử dụng run_stream để tạo luồng SSE Streaming trả về Client
        async def event_generator():
            async for event in agent_engine.run_stream(
                session_id=session_id,
                message=request.message,
                history=request.history
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống Agent: {str(e)}")
