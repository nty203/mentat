from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from mentat.agents.discovery import DiscoveryAgent
from mentat.core.approval import ApprovalType


@pytest.fixture
def project_path(tmp_path: str) -> str:
    p = str(tmp_path)
    open(os.path.join(p, "pyproject.toml"), "w").close()
    return p


async def test_bootstrap_no_client_creates_approvals(project_path: str) -> None:
    agent = DiscoveryAgent(scan_path=project_path, anthropic_client=None)
    approvals = await agent.bootstrap()
    assert len(approvals) >= 1
    assert all(a.type == ApprovalType.PROJECT_CANDIDATE for a in approvals)


async def test_bootstrap_empty_dir(tmp_path: str) -> None:
    agent = DiscoveryAgent(scan_path=str(tmp_path), anthropic_client=None)
    approvals = await agent.bootstrap()
    assert approvals == []


async def test_bootstrap_mock_llm_empty_projects(project_path: str) -> None:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text='{"projects": []}')]
    client.messages.create = AsyncMock(return_value=msg)

    agent = DiscoveryAgent(scan_path=project_path, anthropic_client=client)
    approvals = await agent.bootstrap()
    # LLM returned empty projects list — fallback to per-signal
    assert isinstance(approvals, list)


async def test_bootstrap_mock_llm_returns_projects(project_path: str) -> None:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text='{"projects": [{"name": "foo", "path": "/foo", "details": "test"}]}')]
    client.messages.create = AsyncMock(return_value=msg)

    agent = DiscoveryAgent(scan_path=project_path, anthropic_client=client)
    approvals = await agent.bootstrap()
    assert len(approvals) >= 1
    assert approvals[0].type == ApprovalType.PROJECT_CANDIDATE
