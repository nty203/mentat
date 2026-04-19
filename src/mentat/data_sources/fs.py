from __future__ import annotations

import os

from mentat.core.data_source import DataSourceAdapter, Signal

_MAX_DEPTH = 5
_PROJECT_MARKERS = {"pyproject.toml", "package.json", "Cargo.toml", "go.mod", "setup.py"}


class FsDataSource(DataSourceAdapter):
    async def scan(self, path: str = "") -> list[Signal]:
        if not path:
            path = os.path.expanduser("~")

        if not os.path.isdir(path):
            return []

        signals: list[Signal] = []
        base_depth = path.rstrip(os.sep).count(os.sep)

        for root, dirs, files in os.walk(path, followlinks=False):
            current_depth = root.count(os.sep) - base_depth
            if current_depth >= _MAX_DEPTH:
                dirs.clear()
                continue

            # skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for marker in _PROJECT_MARKERS:
                if marker in files:
                    signals.append(
                        Signal(
                            type="project_root",
                            source="fs",
                            path=root,
                            details=f"{marker} found",
                            metadata={"marker": marker},
                        )
                    )
                    # don't descend into project subdirs
                    dirs.clear()
                    break

        return signals
