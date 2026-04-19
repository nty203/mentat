from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ContextEngine(ABC):
    """Phase 1 stub — context assembly for agent prompts."""

    @abstractmethod
    async def build(self, task: str) -> dict[str, Any]: ...


class NullContextEngine(ContextEngine):
    async def build(self, task: str) -> dict[str, Any]:
        return {}
