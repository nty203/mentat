from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Optional

from mentat.core.approval import ApprovalRequest


class Outcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass
class Example:
    input: str
    output: str


@dataclass
class SkillCard:
    id: str
    name: str
    description: str
    triggers: list[str]
    version: int
    success_rate: float
    usage_count: int


@dataclass
class Skill:
    id: str
    name: str
    description: str
    triggers: list[str]
    body: str
    examples: list[Example]
    tools_used: list[str]
    version: int
    success_rate: float
    usage_count: int
    source: Literal["auto", "manual", "evolved"]
    parent_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillStore(ABC):
    @abstractmethod
    async def list_cards(self, project_id: str | None = None) -> list[SkillCard]: ...

    @abstractmethod
    async def load(self, skill_id: str) -> Skill: ...

    @abstractmethod
    async def match(self, task: str, top_k: int = 3) -> list[SkillCard]: ...

    @abstractmethod
    async def record_usage(self, skill_id: str, outcome: Outcome) -> None: ...

    @abstractmethod
    async def propose(self, skill: Skill) -> ApprovalRequest: ...


class NullSkillStore(SkillStore):
    async def list_cards(self, project_id: str | None = None) -> list[SkillCard]:
        return []

    async def load(self, skill_id: str) -> Skill:
        raise KeyError(f"Skill not found: {skill_id}")

    async def match(self, task: str, top_k: int = 3) -> list[SkillCard]:
        return []

    async def record_usage(self, skill_id: str, outcome: Outcome) -> None:
        pass

    async def propose(self, skill: Skill) -> ApprovalRequest:
        from mentat.core.approval import ApprovalType
        return ApprovalRequest(
            type=ApprovalType.SKILL_PROMOTION,
            data={"skill_id": skill.id, "skill_name": skill.name},
        )
