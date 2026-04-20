from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from mentat.db.migrate import MigrationRunner
from mentat.web.app import web_app


@pytest.fixture
async def client(db_path: str, migrations_dir: str) -> AsyncClient:
    MigrationRunner(db_path, migrations_dir).run()
    web_app.state.db_path = db_path
    from mentat.core.introspection import router as introspection_router
    if not any(getattr(r, "path", None) == "/health" for r in web_app.routes):
        web_app.include_router(introspection_router)
    async with AsyncClient(transport=ASGITransport(app=web_app), base_url="http://test") as c:
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
