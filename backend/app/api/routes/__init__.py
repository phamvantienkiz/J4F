from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.chat import router as chat_router
from app.api.routes.trend import router as trend_router
from app.api.routes.orders import router as orders_router

api_router = APIRouter()

# Đăng ký routes không có prefix
api_router.include_router(health_router)

# Đăng ký routes với prefix /agent
api_router.include_router(chat_router, prefix="/agent", tags=["agent"])
api_router.include_router(trend_router, prefix="/agent", tags=["agent"])

# Đăng ký routes với prefix /api
api_router.include_router(orders_router, prefix="/api", tags=["orders"])
