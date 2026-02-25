"""FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from istari.api.routes import chat, digests, memory, notifications, settings, todos
from istari.config.settings import settings as app_settings
from istari.tools.mcp.client import MCPManager, load_mcp_server_configs


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.basicConfig(
        level=app_settings.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    configs = load_mcp_server_configs()
    async with MCPManager(configs) as manager:
        app.state.mcp_tools = await manager.get_agent_tools()
        yield


app = FastAPI(title="Istari", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(todos.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(digests.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
