from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ApprovalType(str, Enum):
    # Phase 0
    PROJECT_CANDIDATE = "project_candidate"
    # Phase 1
    SKILL_PROMOTION = "skill_promotion"
    SKILL_EVOLUTION = "skill_evolution"
    INTERFACE_CHANGE = "interface_change"
    NEW_WORKER = "new_worker"
    # Phase 2+
    BUDGET_REQUEST = "budget_request"
    EXTERNAL_ACTION = "external_action"
    AGENT_SPAWN = "agent_spawn"


@dataclass
class ApprovalRequest:
    type: ApprovalType
    data: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved: bool | None = None
