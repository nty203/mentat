from __future__ import annotations

import pytest

from mentat.data_sources.git import GitDataSource


async def test_non_git_dir(tmp_path: str) -> None:
    source = GitDataSource()
    signals = await source.scan(str(tmp_path))
    assert signals == []


async def test_empty_path() -> None:
    source = GitDataSource()
    signals = await source.scan("")
    assert signals == []


async def test_nonexistent_path() -> None:
    source = GitDataSource()
    signals = await source.scan("/no/such/path")
    assert signals == []
