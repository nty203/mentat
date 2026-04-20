from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from mentat.__init__ import __version__

router = APIRouter()

# In-memory agent registry (populated by agents at runtime)
_agents: list[dict[str, Any]] = []


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/agents")
async def agents() -> list[dict[str, Any]]:
    return _agents


@router.get("/approvals")
async def approvals(request: Request) -> list[dict[str, Any]]:
    try:
        db_path = str(request.app.state.db_path)
        from mentat.db.repository import ApprovalRepository

        repo = ApprovalRepository(db_path)
        return await repo.list_all()
    except AttributeError:
        return []
