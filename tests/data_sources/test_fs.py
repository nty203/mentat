from __future__ import annotations

import os

import pytest

from mentat.data_sources.fs import FsDataSource


@pytest.fixture
def project_dir(tmp_path: str) -> str:
    p = str(tmp_path)
    open(os.path.join(p, "pyproject.toml"), "w").close()
    return p


async def test_project_root_signal(project_dir: str) -> None:
    source = FsDataSource()
    signals = await source.scan(project_dir)
    assert len(signals) == 1
    assert signals[0].type == "project_root"
    assert signals[0].source == "fs"
    assert "pyproject.toml" in signals[0].details


async def test_nonexistent_path() -> None:
    source = FsDataSource()
    signals = await source.scan("/nonexistent/path/that/does/not/exist")
    assert signals == []


async def test_empty_dir(tmp_path: str) -> None:
    source = FsDataSource()
    signals = await source.scan(str(tmp_path))
    assert signals == []
