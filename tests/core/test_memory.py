from __future__ import annotations

import pytest

from mentat.core.memory import MemoryLayer, SQLiteMemory
from mentat.db.migrate import MigrationRunner


@pytest.fixture
async def memory(db_path: str, migrations_dir: str) -> SQLiteMemory:
    MigrationRunner(db_path, migrations_dir).run()
    return SQLiteMemory(db_path)


async def test_working_write_read(memory: SQLiteMemory) -> None:
    await memory.write(MemoryLayer.WORKING, "foo", "bar")
    result = await memory.read(MemoryLayer.WORKING, "foo")
    assert result == "bar"


async def test_working_missing_key(memory: SQLiteMemory) -> None:
    result = await memory.read(MemoryLayer.WORKING, "nonexistent")
    assert result is None


async def test_episodic_write_read(memory: SQLiteMemory) -> None:
    await memory.write(MemoryLayer.EPISODIC, "note1", {"text": "hello world"})
    result = await memory.read(MemoryLayer.EPISODIC, "note1")
    assert result == {"text": "hello world"}


async def test_episodic_search(memory: SQLiteMemory) -> None:
    await memory.write(MemoryLayer.EPISODIC, "note2", "fts5 search test")
    results = await memory.search(MemoryLayer.EPISODIC, "fts5")
    assert len(results) >= 1
    assert any(r["key"] == "note2" for r in results)


async def test_procedural_write_raises(memory: SQLiteMemory) -> None:
    with pytest.raises(NotImplementedError):
        await memory.write(MemoryLayer.PROCEDURAL, "key", "value")


async def test_working_delete(memory: SQLiteMemory) -> None:
    await memory.write(MemoryLayer.WORKING, "tmp", 42)
    await memory.delete(MemoryLayer.WORKING, "tmp")
    assert await memory.read(MemoryLayer.WORKING, "tmp") is None
