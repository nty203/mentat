from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class MemoryLayer(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class Memory(ABC):
    @abstractmethod
    async def write(self, layer: MemoryLayer, key: str, value: Any) -> None: ...

    @abstractmethod
    async def read(self, layer: MemoryLayer, key: str) -> Any | None: ...

    @abstractmethod
    async def search(self, layer: MemoryLayer, query: str, top_k: int = 5) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def delete(self, layer: MemoryLayer, key: str) -> None: ...


class SQLiteMemory(Memory):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._working: dict[str, Any] = {}

    async def write(self, layer: MemoryLayer, key: str, value: Any) -> None:
        if layer == MemoryLayer.PROCEDURAL:
            raise NotImplementedError("Use SkillStore.propose() for procedural memory")
        if layer == MemoryLayer.WORKING:
            self._working[key] = value
            return
        # EPISODIC — persist to SQLite
        import json
        import aiosqlite
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO memory_entries (key, value, layer) VALUES (?, ?, ?)",
                (key, json.dumps(value), layer.value),
            )
            await db.commit()

    async def read(self, layer: MemoryLayer, key: str) -> Any | None:
        if layer == MemoryLayer.PROCEDURAL:
            raise NotImplementedError("Use SkillStore for procedural memory")
        if layer == MemoryLayer.WORKING:
            return self._working.get(key)
        import json
        import aiosqlite
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT value FROM memory_entries WHERE key = ? AND layer = ?",
                (key, layer.value),
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else None

    async def search(self, layer: MemoryLayer, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if layer != MemoryLayer.EPISODIC:
            return []
        import json
        import aiosqlite
        results: list[dict[str, Any]] = []
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT key, value FROM memory_fts WHERE memory_fts MATCH ? LIMIT ?",
                (query, top_k),
            ) as cursor:
                async for row in cursor:
                    results.append({"key": row[0], "value": json.loads(row[1])})
        return results

    async def delete(self, layer: MemoryLayer, key: str) -> None:
        if layer == MemoryLayer.WORKING:
            self._working.pop(key, None)
            return
        if layer == MemoryLayer.PROCEDURAL:
            raise NotImplementedError("Use SkillStore for procedural memory")
        import aiosqlite
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM memory_entries WHERE key = ? AND layer = ?",
                (key, layer.value),
            )
            await db.commit()
