from __future__ import annotations

import os
import tempfile
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from mentat.core.data_source import Signal


@pytest.fixture
def db_path(tmp_path: Any) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture
def migrations_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "migrations")


@pytest.fixture
def mock_anthropic() -> MagicMock:
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text='{"projects": []}')]
    client.messages.create = AsyncMock(return_value=message)
    return client


@pytest.fixture
def sample_signals() -> list[Signal]:
    return [
        Signal(
            type="project_root",
            source="fs",
            path="/home/user/projects/foo",
            details="pyproject.toml found",
        ),
        Signal(
            type="recent_commits",
            source="git",
            path="/home/user/projects/foo",
            details="5 commits (last: 2h ago)",
        ),
    ]
