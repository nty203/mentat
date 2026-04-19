from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class HeartbeatContext:
    agent_id: str
    status: AgentStatus
    task: str | None = None
    progress: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class Agent(ABC):
    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.status = AgentStatus.IDLE

    @abstractmethod
    async def run(self) -> None: ...

    @abstractmethod
    async def heartbeat(self) -> HeartbeatContext: ...

    @abstractmethod
    async def stop(self) -> None: ...
