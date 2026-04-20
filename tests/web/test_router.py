from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from mentat.db.migrate import MigrationRunner
from mentat.web.app import web_app


@pytest.fixture
async def client(db_path: str, migrations_dir: str) -> AsyncClient:
    MigrationRunner(db_path, migrations_dir).run()
    web_app.state.db_path = db_path
    # include introspection router lazily (avoid duplicate include across tests)
    from mentat.core.introspection import router as introspection_router
    if not any(r.path == "/health" for r in web_app.routes):  # type: ignore[attr-defined]
        web_app.include_router(introspection_router)
    async with AsyncClient(transport=ASGITransport(app=web_app), base_url="http://test") as c:
        yield c


async def test_index(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    assert b"mentat" in resp.content


async def test_approvals_partial_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/approvals")
    assert resp.status_code == 200
    assert b"mentat bootstrap" in resp.content


async def test_approve_nonexistent(client: AsyncClient) -> None:
    resp = await client.post("/api/approvals/nonexistent/approve")
    assert resp.status_code == 200


async def test_reject_nonexistent(client: AsyncClient) -> None:
    resp = await client.post("/api/approvals/nonexistent/reject")
    assert resp.status_code == 200


async def test_projects_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/projects")
    assert resp.status_code == 200


async def test_project_detail_missing(client: AsyncClient) -> None:
    resp = await client.get("/api/projects/no-such-id")
    assert resp.status_code == 200


async def test_chat_history_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/chat/history")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_chat_empty_message(client: AsyncClient) -> None:
    resp = await client.post("/api/chat", data={"message": ""})
    assert resp.status_code == 200
