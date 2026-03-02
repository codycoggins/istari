"""Tests for token utilities, auth routes, and auth middleware."""

import httpx
import pytest

from istari.api.auth import COOKIE_NAME, sign_token, verify_token

_SECRET = "test-secret-key-32-chars-long-!!"
_PASSWORD = "hunter2"


# ── Token utilities ───────────────────────────────────────────────────────────


class TestTokenUtils:
    def test_roundtrip(self) -> None:
        assert verify_token(sign_token(_SECRET), _SECRET)

    def test_wrong_key(self) -> None:
        assert not verify_token(sign_token(_SECRET), "wrong-key")

    def test_empty_token(self) -> None:
        assert not verify_token("", _SECRET)

    def test_empty_key(self) -> None:
        assert not verify_token(sign_token(_SECRET), "")

    def test_garbage_token(self) -> None:
        assert not verify_token("notavalidtoken", _SECRET)

    def test_tampered_token(self) -> None:
        token = sign_token(_SECRET)
        tampered = token[:-4] + "XXXX"
        assert not verify_token(tampered, _SECRET)


# ── Shared fixture ────────────────────────────────────────────────────────────


@pytest.fixture()
def auth_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from istari.config import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "app_secret_key", _SECRET)
    monkeypatch.setattr(settings_module.settings, "app_password", _PASSWORD)
    monkeypatch.setattr(settings_module.settings, "cookie_secure", False)


# ── Auth routes ───────────────────────────────────────────────────────────────


class TestAuthRoutes:
    async def test_login_success(self, auth_settings: None) -> None:
        from istari.api.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/auth/login", json={"password": _PASSWORD})
        assert r.status_code == 200
        assert COOKIE_NAME in r.cookies

    async def test_login_wrong_password(self, auth_settings: None) -> None:
        from istari.api.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/auth/login", json={"password": "wrong"})
        assert r.status_code == 401

    async def test_logout_clears_cookie(self, auth_settings: None) -> None:
        from istari.api.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/auth/logout")
        assert r.status_code == 200

    async def test_me_authenticated(self, auth_settings: None) -> None:
        from istari.api.main import app

        token = sign_token(_SECRET)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(COOKIE_NAME, token)
            r = await client.get("/api/auth/me")
        assert r.status_code == 200

    async def test_me_unauthenticated(self, auth_settings: None) -> None:
        from istari.api.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get("/api/auth/me")
        assert r.status_code == 401

    async def test_login_not_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Login returns 503 when APP_SECRET_KEY is not set."""
        from istari.api.main import app
        from istari.config import settings as settings_module

        monkeypatch.setattr(settings_module.settings, "app_secret_key", "")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/auth/login", json={"password": "anything"})
        assert r.status_code == 503


# ── Middleware ────────────────────────────────────────────────────────────────


class TestAuthMiddleware:
    async def test_health_always_accessible(self, auth_settings: None) -> None:
        from istari.api.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get("/health")
        assert r.status_code == 200

    async def test_login_endpoint_accessible_without_cookie(
        self, auth_settings: None
    ) -> None:
        from istari.api.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/auth/login", json={"password": _PASSWORD})
        assert r.status_code == 200

    async def test_protected_route_blocked_without_cookie(
        self, auth_settings: None
    ) -> None:
        from istari.api.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get("/api/todos/")
        assert r.status_code == 401

    async def test_protected_route_allowed_with_valid_cookie(
        self, auth_settings: None
    ) -> None:
        from istari.api.main import app

        token = sign_token(_SECRET)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.cookies.set(COOKIE_NAME, token)
            r = await client.get("/api/auth/me")
        # Middleware passed; handler ran and confirmed the cookie is valid
        assert r.status_code == 200

    async def test_auth_disabled_when_no_secret_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from istari.api.main import app
        from istari.config import settings as settings_module

        monkeypatch.setattr(settings_module.settings, "app_secret_key", "")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # /api/auth/me returns 200 when auth is disabled
            r = await client.get("/api/auth/me")
        assert r.status_code == 200
