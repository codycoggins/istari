"""FastAPI application factory."""

import logging
import logging.handlers
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from istari.api.debug import ring_buffer
from istari.api.middleware.auth import AuthMiddleware
from istari.api.routes import auth, chat, digests, memory, notifications, projects, settings, todos
from istari.api.routes import debug as debug_routes
from istari.config.settings import settings as app_settings
from istari.tools.mcp.client import MCPManager, load_mcp_server_configs

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
_LOG_DATEFMT = "%H:%M:%S"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.basicConfig(
        level=app_settings.log_level.upper(),
        format=_LOG_FORMAT,
        datefmt=_LOG_DATEFMT,
    )
    root = logging.getLogger()

    # Pin noisy third-party loggers to WARNING regardless of LOG_LEVEL.
    # - LiteLLM: suppress_debug_info kills print()s but not the Python logger
    # - openai: HTTP-level request/response traces from the OpenAI SDK
    # - googleapiclient: discovery-doc fetches on every Calendar/Gmail call
    # - urllib3/httpx: connection pool chatter
    # - h2/rustls/hyper_util/primp/cookie_store: Rust HTTP/2 client internals
    #   emitted by the web_search tool's underlying primp/reqwest stack
    for _noisy_logger in [
        "LiteLLM",
        "openai",
        "googleapiclient",
        "urllib3",
        "httpx",
        "h2",
        "rustls",
        "hyper_util",
        "primp",
        "cookie_store",
    ]:
        logging.getLogger(_noisy_logger).setLevel(logging.WARNING)

    # Rotating file handler — survives container restarts via volume mount
    log_dir = Path("/app/logs")
    if log_dir.exists():
        fh = logging.handlers.RotatingFileHandler(
            log_dir / "api.log",
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
        )
        fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
        root.addHandler(fh)

    # In-process ring buffer for /api/debug/recent-errors
    root.addHandler(ring_buffer)

    configs = load_mcp_server_configs()
    async with MCPManager(configs) as manager:
        app.state.mcp_tools = await manager.get_agent_tools()
        yield


app = FastAPI(title="Istari", version="0.1.0", lifespan=lifespan)

# Auth middleware must be added first (outermost layer) so it runs before CORS
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(todos.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(digests.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(debug_routes.router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
