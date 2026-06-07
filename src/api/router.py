from fastapi import APIRouter

from src.api.routes import agent, health, text_to_api


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(text_to_api.router)
api_router.include_router(agent.router)
