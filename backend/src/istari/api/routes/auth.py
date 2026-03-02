"""Authentication endpoints — login, logout, session check."""

import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from istari.api.auth import COOKIE_NAME, sign_token, verify_token
from istari.config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_MAX_AGE = 86400 * 30  # 30 days


class LoginRequest(BaseModel):
    password: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


@router.post("/login")
async def login(body: LoginRequest, response: Response) -> dict[str, str]:
    if not settings.app_secret_key:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(body.password, settings.app_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = sign_token(settings.app_secret_key)
    _set_session_cookie(response, token)
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    _clear_session_cookie(response)
    return {"status": "ok"}


@router.get("/me")
async def me(request: Request) -> dict[str, str]:
    # Auth disabled — always authenticated
    if not settings.app_secret_key:
        return {"status": "ok"}
    token = request.cookies.get(COOKIE_NAME, "")
    if not verify_token(token, settings.app_secret_key):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"status": "ok"}
