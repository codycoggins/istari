"""Pure ASGI authentication middleware.

Blocks all HTTP requests that lack a valid session cookie, except for a small
set of exempt paths.  WebSocket upgrade requests pass through here and perform
their own cookie check inside the endpoint handler.

Auth is disabled entirely when ``settings.app_secret_key`` is empty, so local
dev without env vars set continues to work as before.
"""

import logging
from collections.abc import Callable, Coroutine
from http.cookies import SimpleCookie
from typing import Any

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from istari.api.auth import COOKIE_NAME, verify_token
from istari.config.settings import settings

logger = logging.getLogger(__name__)

_EXEMPT_PATHS = {"/health", "/api/auth/login", "/api/auth/logout"}

_CallNext = Callable[[Scope, Receive, Send], Coroutine[Any, Any, None]]


def _cookie_from_headers(headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    for name, value in headers:
        if name.lower() == b"cookie":
            jar = SimpleCookie()
            jar.load(value.decode(errors="replace"))
            return {k: m.value for k, m in jar.items()}
    return {}


class AuthMiddleware:
    """Rejects unauthenticated HTTP requests with 401.

    Skips auth when ``APP_SECRET_KEY`` is not configured (development mode).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Auth disabled — pass everything through
        if not settings.app_secret_key:
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        if path in _EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        # WebSocket auth is handled inside the endpoint via ws.cookies
        if scope["type"] == "websocket":
            await self.app(scope, receive, send)
            return

        # HTTP: require valid session cookie
        cookies = _cookie_from_headers(scope.get("headers", []))
        token = cookies.get(COOKIE_NAME, "")
        if not verify_token(token, settings.app_secret_key):
            response = JSONResponse({"detail": "Not authenticated"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
