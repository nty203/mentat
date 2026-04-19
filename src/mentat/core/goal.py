from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Goal:
    """Phase 1 stub."""

    id: str
    description: str
    metadata: dict[str, Any]


class GoalStore(ABC):
    """Phase 1 stub."""

    @abstractmethod
    async def list(self) -> list[Goal]: ...

    @abstractmethod
    async def add(self, goal: Goal) -> None: ...

    @abstractmethod
    async def remove(self, goal_id: str) -> None: ...
