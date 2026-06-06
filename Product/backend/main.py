import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure Product/ directory is in python module path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.config import settings
from backend.app.api.v1 import auth, chat, order
from backend.app.db.session import engine
from backend.app.db.base import Base

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS Middleware
# Allow all origins for development ease in Hackathon MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Router Endpoints
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["Chat & Agent"])
app.include_router(order.router, prefix=f"{settings.API_V1_STR}/order", tags=["Orders"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to BurgerPrints Agent API Gateway",
        "version": "0.1.0",
        "docs_url": "/docs"
    }

@app.on_event("startup")
async def startup_event():
    # Automatically initialize SQLite tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("FastAPI Backend and Database started successfully.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
