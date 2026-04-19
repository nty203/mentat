from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from mentat.core.introspection import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


async def test_agents_empty(client: AsyncClient) -> None:
    resp = await client.get("/agents")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_approvals_empty(client: AsyncClient) -> None:
    resp = await client.get("/approvals")
    assert resp.status_code == 200
    assert resp.json() == []
