from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserProfile:
    user_id: str
    name: str
    preferences: dict[str, Any] = field(default_factory=dict)


class UserModel(ABC):
    @abstractmethod
    async def get_profile(self, user_id: str) -> UserProfile | None: ...

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> None: ...

    @abstractmethod
    async def record_feedback(self, user_id: str, task_id: str, feedback: str) -> None: ...


class SQLiteUserModel(UserModel):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def get_profile(self, user_id: str) -> UserProfile | None:
        import json
        import aiosqlite
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT name, preferences FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return UserProfile(
                    user_id=user_id,
                    name=row[0],
                    preferences=json.loads(row[1]),
                )

    async def save_profile(self, profile: UserProfile) -> None:
        import json
        import aiosqlite
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_profiles (user_id, name, preferences) VALUES (?, ?, ?)",
                (profile.user_id, profile.name, json.dumps(profile.preferences)),
            )
            await db.commit()

    async def record_feedback(self, user_id: str, task_id: str, feedback: str) -> None:
        import aiosqlite
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO user_feedback (user_id, task_id, feedback) VALUES (?, ?, ?)",
                (user_id, task_id, feedback),
            )
            await db.commit()
