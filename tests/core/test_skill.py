from __future__ import annotations

import pytest

from mentat.core.skill import NullSkillStore, Outcome, Skill


@pytest.fixture
def store() -> NullSkillStore:
    return NullSkillStore()


async def test_list_cards_empty(store: NullSkillStore) -> None:
    assert await store.list_cards() == []


async def test_match_empty(store: NullSkillStore) -> None:
    assert await store.match("do something") == []


async def test_load_raises(store: NullSkillStore) -> None:
    with pytest.raises(KeyError):
        await store.load("nonexistent")


async def test_record_usage_noop(store: NullSkillStore) -> None:
    await store.record_usage("any", Outcome.SUCCESS)  # should not raise


async def test_propose_returns_approval(store: NullSkillStore) -> None:
    skill = Skill(
        id="s1", name="test", description="desc", triggers=[],
        body="", examples=[], tools_used=[], version=1,
        success_rate=0.0, usage_count=0, source="manual",
    )
    req = await store.propose(skill)
    assert req.type.value == "skill_promotion"
