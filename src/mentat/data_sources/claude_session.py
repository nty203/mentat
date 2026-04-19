from __future__ import annotations

from mentat.core.data_source import DataSourceAdapter, Signal


class ClaudeSessionDataSource(DataSourceAdapter):
    """Phase 0 stub — returns empty list. Phase 1 will read Claude session patterns."""

    async def scan(self, path: str = "") -> list[Signal]:
        return []
