from __future__ import annotations

from mentat.data_sources.claude_session import ClaudeSessionDataSource


async def test_stub_returns_empty() -> None:
    source = ClaudeSessionDataSource()
    signals = await source.scan()
    assert signals == []
