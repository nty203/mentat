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


class RunRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def create_run(self, agent_id: str, task: str, progress: str = "") -> str:
        import uuid
        run_id = str(uuid.uuid4())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO agent_runs (id, agent_id, task, status, progress, started_at)"
                " VALUES (?, ?, ?, 'running', ?, datetime('now'))",
                (run_id, agent_id, task, progress),
            )
            await db.commit()
        return run_id

    async def update_run(
        self, run_id: str, status: str, result: str = "", progress: str = ""
    ) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE agent_runs SET status=?, result=?, progress=?,"
                " finished_at=datetime('now') WHERE id=?",
                (status, result, progress, run_id),
            )
            await db.commit()

    async def set_progress(self, run_id: str, progress: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE agent_runs SET progress=? WHERE id=?",
                (progress, run_id),
            )
            await db.commit()

    async def list_active(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, agent_id, task, status, progress, result, started_at, finished_at"
                " FROM agent_runs WHERE status='running' ORDER BY started_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, agent_id, task, status, progress, result, started_at, finished_at"
                " FROM agent_runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get(self, run_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, agent_id, task, status, progress, result, started_at, finished_at"
                " FROM agent_runs WHERE id = ?",
                (run_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return dict(row) if row else None


class SkillRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def list_all(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, description, triggers, source, version,"
                " success_rate, usage_count, created_at"
                " FROM skills ORDER BY usage_count DESC, created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["triggers"] = json.loads(d["triggers"])
            result.append(d)
        return result

    async def get(self, skill_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, description, triggers, body, examples, tools_used,"
                " source, version, success_rate, usage_count, parent_id, created_at"
                " FROM skills WHERE id = ?",
                (skill_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        for field in ("triggers", "examples", "tools_used"):
            d[field] = json.loads(d[field])
        return d


_COST_PER_M: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    "claude-haiku-4-5": (0.80, 4.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (15.0, 75.0),
    "claude-3-5-haiku@20241022": (0.80, 4.0),
    "claude-3-5-sonnet-v2@20241022": (3.0, 15.0),
    "claude-3-opus@20240229": (15.0, 75.0),
}


def _estimate_cost(by_model: dict[str, dict[str, int]]) -> float:
    total = 0.0
    for model, usage in by_model.items():
        rates = _COST_PER_M.get(model, (3.0, 15.0))
        total += usage["input"] / 1_000_000 * rates[0]
        total += usage["output"] / 1_000_000 * rates[1]
    return round(total, 4)


class TokenRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO token_usage (model, input_tokens, output_tokens) VALUES (?, ?, ?)",
                (model, input_tokens, output_tokens),
            )
            await db.commit()

    async def totals(self) -> dict[str, Any]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT model, SUM(input_tokens) as input, SUM(output_tokens) as output"
                " FROM token_usage GROUP BY model"
            ) as cursor:
                rows = await cursor.fetchall()
            async with db.execute(
                "SELECT SUM(input_tokens) as ti, SUM(output_tokens) as to_"
                " FROM token_usage"
            ) as cursor:
                totals_row = await cursor.fetchone()
        by_model = {r["model"]: {"input": r["input"] or 0, "output": r["output"] or 0} for r in rows}
        total_input = (totals_row["ti"] or 0) if totals_row else 0
        total_output = (totals_row["to_"] or 0) if totals_row else 0
        return {
            "total_input": total_input,
            "total_output": total_output,
            "total_tokens": total_input + total_output,
            "by_model": by_model,
            "estimated_cost_usd": _estimate_cost(by_model),
        }

    async def reset(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM token_usage")
            await db.commit()


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
