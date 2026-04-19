from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkerTemplate:
    name: str
    description: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkerTemplateStore:
    def __init__(self, templates_dir: str) -> None:
        self._dir = templates_dir

    def list(self) -> list[str]:
        if not os.path.isdir(self._dir):
            return []
        return [
            f[:-3] for f in os.listdir(self._dir) if f.endswith(".md")
        ]

    def load(self, name: str) -> WorkerTemplate:
        path = os.path.join(self._dir, f"{name}.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        metadata: dict[str, Any] = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import re
                for line in parts[1].strip().splitlines():
                    m = re.match(r"^(\w+):\s*(.+)$", line)
                    if m:
                        metadata[m.group(1)] = m.group(2).strip()
                body = parts[2].strip()

        return WorkerTemplate(
            name=name,
            description=str(metadata.get("description", "")),
            body=body,
            metadata=metadata,
        )
