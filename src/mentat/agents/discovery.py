from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from mentat.core.approval import ApprovalRequest, ApprovalType
from mentat.core.data_source import Signal
from mentat.data_sources.claude_session import ClaudeSessionDataSource
from mentat.data_sources.fs import FsDataSource
from mentat.data_sources.git import GitDataSource


class DiscoveryAgent:
    def __init__(
        self,
        scan_path: str = "",
        anthropic_client: Any = None,
        db_path: str | None = None,
    ) -> None:
        self._path = scan_path or os.path.expanduser("~")
        self._client = anthropic_client
        self._db_path = db_path
        self._fs = FsDataSource()
        self._git = GitDataSource()
        self._claude = ClaudeSessionDataSource()

    async def scan(self) -> list[Signal]:
        results = await asyncio.gather(
            self._fs.scan(self._path),
            self._git.scan(self._path),
            self._claude.scan(),
            return_exceptions=True,
        )
        signals: list[Signal] = []
        for r in results:
            if isinstance(r, list):
                signals.extend(r)
        return signals

    async def bootstrap(self) -> list[ApprovalRequest]:
        signals = await self.scan()

        project_roots = [s for s in signals if s.type == "project_root"]

        if not project_roots:
            return []

        projects = await self._cluster_projects(project_roots)

        approvals: list[ApprovalRequest] = []
        for project in projects:
            req = ApprovalRequest(
                type=ApprovalType.PROJECT_CANDIDATE,
                data=project,
            )
            approvals.append(req)

        if self._db_path:
            await self._persist(approvals)

        return approvals

    async def _persist(self, approvals: list[ApprovalRequest]) -> None:
        from mentat.db.repository import ApprovalRepository

        repo = ApprovalRepository(self._db_path)  # type: ignore[arg-type]
        for req in approvals:
            await repo.save(req)

    async def _cluster_projects(self, signals: list[Signal]) -> list[dict[str, Any]]:
        if self._client is None:
            return [
                {"name": os.path.basename(s.path), "path": s.path, "details": s.details}
                for s in signals
            ]

        paths_text = "\n".join(f"- {s.path} ({s.details})" for s in signals)
        prompt = (
            f"Given these project directories found on disk:\n{paths_text}\n\n"
            "Return a JSON object with a 'projects' key containing an array of "
            "project objects, each with 'name', 'path', and 'details' fields. "
            "Cluster related directories into single projects where appropriate."
        )

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            data = json.loads(text)
            return list(data.get("projects", []))
        except Exception:
            return [
                {"name": os.path.basename(s.path), "path": s.path, "details": s.details}
                for s in signals
            ]
