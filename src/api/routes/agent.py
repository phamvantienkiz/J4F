import requests
from fastapi import APIRouter, HTTPException, Query

from src.agent.agents.market_suggestion_agent import MarketSuggestionAgent
from src.agent.service import AgentService
from src.api.routes.health import is_ready, readiness_error
from src.api.schemas.agent import AgentChatRequest


router = APIRouter(prefix="/agent", tags=["agent"])
agent_service = AgentService()
suggestion_agent = MarketSuggestionAgent()


@router.get("/suggestions")
def suggestions(country: str = Query("US", min_length=2, max_length=3), month: int | None = Query(None, ge=1, le=12)):
    return suggestion_agent.run(country, month)


@router.post("/chat")
def chat(request: AgentChatRequest):
    if not is_ready():
        detail = readiness_error() or "Server đang warm up Catalog API, thử lại sau vài giây."
        raise HTTPException(status_code=503, detail=detail)
    try:
        return agent_service.chat(request.message, request.history, request.session_id)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except requests.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else 502
        detail = error.response.text if error.response is not None else str(error)
        raise HTTPException(status_code=status_code, detail=detail) from error
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
