from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: Any
    error: str | None = None


class ToolAdapter(ABC):
    @abstractmethod
    async def call(self, name: str, arguments: dict[str, Any]) -> ToolResult: ...
