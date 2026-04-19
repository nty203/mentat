from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Signal:
    type: str
    source: str
    path: str
    details: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DataSourceAdapter(ABC):
    @abstractmethod
    async def scan(self, path: str = "") -> list[Signal]: ...
