"""Async client for the Todoist API v1.

Thin httpx wrapper covering the endpoints the migration script needs. The legacy
``/rest/v2`` API is deprecated (returns 410); this targets the current
``/api/v1`` endpoints, whose GET list responses are cursor-paginated
(``{"results": [...], "next_cursor": ...}``).

All non-2xx responses raise ``TodoistError``; a project-limit rejection on
project creation raises the more specific ``TodoistProjectLimitError`` (the
signal that the account's plan-imposed project limit has been reached).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.todoist.com/api/v1"


class TodoistError(Exception):
    """A Todoist API call returned a non-success status."""


class TodoistProjectLimitError(TodoistError):
    """Project creation was rejected — the account's project limit is reached."""


class TodoistClient:
    """Minimal async Todoist API v1 client."""

    def __init__(self, token: str, *, client: httpx.AsyncClient | None = None) -> None:
        if not token:
            raise ValueError("Todoist API token is required")
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def __aenter__(self) -> TodoistClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def list_projects(self) -> list[dict[str, Any]]:
        return await self._get_all("/projects")

    async def create_project(self, name: str) -> dict[str, Any]:
        resp = await self._client.post("/projects", json={"name": name})
        if self._is_project_limit(resp):
            raise TodoistProjectLimitError(
                f"Todoist rejected project {name!r} "
                f"({resp.status_code}): {resp.text}"
            )
        project: dict[str, Any] = self._json(resp)
        return project

    async def list_tasks(self, project_id: str) -> list[dict[str, Any]]:
        return await self._get_all("/tasks", params={"project_id": project_id})

    async def create_task(self, **fields: Any) -> dict[str, Any]:
        resp = await self._client.post("/tasks", json=fields)
        task: dict[str, Any] = self._json(resp)
        return task

    async def create_comment(self, project_id: str, content: str) -> dict[str, Any]:
        resp = await self._client.post(
            "/comments", json={"project_id": project_id, "content": content}
        )
        comment: dict[str, Any] = self._json(resp)
        return comment

    async def _get_all(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Follow ``next_cursor`` pagination and return the flattened results."""
        items: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            query = dict(params or {})
            if cursor:
                query["cursor"] = cursor
            resp = await self._client.get(path, params=query)
            data = self._json(resp)
            items.extend(data["results"])
            cursor = data.get("next_cursor")
            if not cursor:
                return items

    @staticmethod
    def _is_project_limit(resp: httpx.Response) -> bool:
        """A plan project-limit rejection (402/403, or a body mentioning a limit)."""
        if resp.is_success:
            return False
        if resp.status_code in (httpx.codes.PAYMENT_REQUIRED, httpx.codes.FORBIDDEN):
            return True
        return "limit" in resp.text.lower()

    @staticmethod
    def _json(resp: httpx.Response) -> Any:
        if not resp.is_success:
            raise TodoistError(
                f"{resp.request.method} {resp.request.url} "
                f"-> {resp.status_code}: {resp.text}"
            )
        return resp.json()
