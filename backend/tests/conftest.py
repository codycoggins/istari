"""Shared test fixtures: test DB, sessions, mocks."""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
