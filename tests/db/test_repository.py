from __future__ import annotations

import pytest

from mentat.core.approval import ApprovalRequest, ApprovalType
from mentat.db.migrate import MigrationRunner
from mentat.db.repository import ApprovalRepository, ChatRepository, ProjectRepository


@pytest.fixture
async def migrated_db(db_path: str, migrations_dir: str) -> str:
    MigrationRunner(db_path, migrations_dir).run()
    return db_path


# ── ApprovalRepository ────────────────────────────────────────────────────────

async def test_save_and_list_pending(migrated_db: str) -> None:
    repo = ApprovalRepository(migrated_db)
    req = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "foo", "path": "/foo"})
    await repo.save(req)
    pending = await repo.list_pending()
    assert len(pending) == 1
    assert pending[0].id == req.id
    assert pending[0].data["name"] == "foo"


async def test_approve_sets_approved(migrated_db: str) -> None:
    repo = ApprovalRepository(migrated_db)
    req = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "bar", "path": "/bar"})
    await repo.save(req)
    result = await repo.approve(req.id)
    assert result is True
    pending = await repo.list_pending()
    assert all(r.id != req.id for r in pending)


async def test_reject_sets_rejected(migrated_db: str) -> None:
    repo = ApprovalRepository(migrated_db)
    req = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "baz", "path": "/baz"})
    await repo.save(req)
    result = await repo.reject(req.id)
    assert result is True
    pending = await repo.list_pending()
    assert all(r.id != req.id for r in pending)


async def test_approve_idempotent(migrated_db: str) -> None:
    repo = ApprovalRepository(migrated_db)
    req = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "dup", "path": "/dup"})
    await repo.save(req)
    await repo.approve(req.id)
    # second approve on already-approved row — should not error
    result2 = await repo.approve(req.id)
    assert result2 is False  # no rows changed (already approved)


async def test_list_pending_excludes_decided(migrated_db: str) -> None:
    repo = ApprovalRepository(migrated_db)
    req1 = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "p1", "path": "/p1"})
    req2 = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "p2", "path": "/p2"})
    await repo.save(req1)
    await repo.save(req2)
    await repo.approve(req1.id)
    pending = await repo.list_pending()
    ids = [r.id for r in pending]
    assert req1.id not in ids
    assert req2.id in ids


async def test_save_duplicate_ignored(migrated_db: str) -> None:
    repo = ApprovalRepository(migrated_db)
    req = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "once", "path": "/once"})
    await repo.save(req)
    await repo.save(req)  # duplicate — should not raise
    assert len(await repo.list_pending()) == 1


# ── ProjectRepository ─────────────────────────────────────────────────────────

async def test_project_save_and_list(migrated_db: str) -> None:
    repo = ProjectRepository(migrated_db)
    pid = await repo.save(name="mentat", path="/home/user/mentat", metadata={"source": "fs"})
    projects = await repo.list_all()
    assert len(projects) == 1
    assert projects[0]["name"] == "mentat"
    assert projects[0]["metadata"]["source"] == "fs"

    got = await repo.get(pid)
    assert got is not None
    assert got["path"] == "/home/user/mentat"


async def test_project_get_missing(migrated_db: str) -> None:
    repo = ProjectRepository(migrated_db)
    assert await repo.get("nonexistent-id") is None


# ── ChatRepository ────────────────────────────────────────────────────────────

async def test_chat_save_and_history(migrated_db: str) -> None:
    repo = ChatRepository(migrated_db)
    await repo.save(role="user", content="hello")
    await repo.save(role="assistant", content="hi there")
    history = await repo.history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


async def test_chat_history_limit(migrated_db: str) -> None:
    repo = ChatRepository(migrated_db)
    for i in range(10):
        await repo.save(role="user", content=f"msg {i}")
    history = await repo.history(limit=5)
    assert len(history) == 5
