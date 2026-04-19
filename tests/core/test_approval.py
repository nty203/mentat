from __future__ import annotations

from mentat.core.approval import ApprovalRequest, ApprovalType


def test_approval_request_defaults() -> None:
    req = ApprovalRequest(type=ApprovalType.PROJECT_CANDIDATE, data={"name": "foo"})
    assert req.id
    assert req.created_at
    assert req.approved is None


def test_approval_type_values() -> None:
    assert ApprovalType.PROJECT_CANDIDATE == "project_candidate"
    assert ApprovalType.SKILL_PROMOTION == "skill_promotion"
    assert len(ApprovalType) == 8
