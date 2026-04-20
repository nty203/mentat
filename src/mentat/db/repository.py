from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite

from mentat.core.approval import ApprovalRequest, ApprovalType


class ApprovalRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, request: ApprovalRequest) -> None:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO approval_requests (id, type, data, approved, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (
                        request.id,
                        request.type.value,
                        json.dumps(request.data),
                        None,
                        request.created_at.isoformat(),
                    ),
                )
                await db.commit()
        except Exception as e:
            import sys
            print(f"[mentat] ApprovalRepository.save error: {e}", file=sys.stderr)

    async def list_pending(self) -> list[ApprovalRequest]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, type, data, approved, created_at FROM approval_requests"
                " WHERE approved IS NULL ORDER BY created_at ASC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [_row_to_approval(dict(r)) for r in rows]

    async def list_all(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, type, data, approved, created_at FROM approval_requests"
                " ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def approve(self, request_id: str) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE approval_requests SET approved = 1 WHERE id = ? AND approved IS NULL",
                (request_id,),
            )
            await db.commit()
            return db.total_changes > 0

    async def reject(self, request_id: str) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE approval_requests SET approved = 0 WHERE id = ? AND approved IS NULL",
                (request_id,),
            )
            await db.commit()
            return db.total_changes > 0


def _row_to_approval(row: dict[str, Any]) -> ApprovalRequest:
    return ApprovalRequest(
        id=row["id"],
        type=ApprovalType(row["type"]),
        data=json.loads(row["data"]),
        approved=None if row["approved"] is None else bool(row["approved"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class ProjectRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, name: str, path: str, metadata: dict[str, Any] | None = None) -> str:
        import uuid
        project_id = str(uuid.uuid4())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO projects (id, name, path, metadata) VALUES (?, ?, ?, ?)",
                (project_id, name, path, json.dumps(metadata or {})),
            )
            await db.commit()
        return project_id

    async def list_all(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, path, metadata, created_at FROM projects ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["metadata"] = json.loads(d["metadata"])
            result.append(d)
        return result

    async def get(self, project_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, path, metadata, created_at FROM projects WHERE id = ?",
                (project_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"])
        return d


class ChatRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, role: str, content: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO chat_messages (role, content) VALUES (?, ?)",
                (role, content),
            )
            await db.commit()

    async def history(self, limit: int = 100) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, role, content, created_at FROM chat_messages"
                " ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]
