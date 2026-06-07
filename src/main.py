import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agent.service import AgentService
from src.api.router import api_router
from src.api.routes.health import mark_warmup_finished, mark_warmup_started
from src.core.config import settings
from src.services.catalog_client import CatalogApiClient


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def _warm_up_dependencies():
    AgentService()
    CatalogApiClient(timeout=5).list_catalogs()


@app.on_event("startup")
async def warm_up_before_ready():
    mark_warmup_started()
    async def run_warmup():
        try:
            await asyncio.to_thread(_warm_up_dependencies)
            mark_warmup_finished()
        except Exception as error:
            mark_warmup_finished(str(error))

    asyncio.create_task(run_warmup())
