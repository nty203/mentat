from __future__ import annotations

import os
from enum import Enum
from typing import AsyncGenerator


class Intent(str, Enum):
    APPROVE_ALL = "approve_all"
    REJECT_ALL = "reject_all"
    SCAN = "scan"
    LIST = "list"
    UNKNOWN = "unknown"


_APPROVE_KW = {"승인", "approve", "yes", "y", "응", "ok", "ㅇㅋ"}
_REJECT_KW = {"거절", "reject", "no", "n", "아니"}
_SCAN_KW = {"스캔", "scan", "찾아", "검색"}
_LIST_KW = {"목록", "list", "보여", "현황"}
_NEGATE_KW = {"안", "말고", "아니", "no", "not", "don't"}


def route(msg: str) -> Intent:
    words = set(msg.lower().split())
    if words & _NEGATE_KW and words & (_APPROVE_KW | _REJECT_KW):
        return Intent.UNKNOWN
    if words & _APPROVE_KW:
        return Intent.APPROVE_ALL
    if words & _REJECT_KW:
        return Intent.REJECT_ALL
    if words & _SCAN_KW:
        return Intent.SCAN
    if words & _LIST_KW:
        return Intent.LIST
    return Intent.UNKNOWN


async def generate_response(message: str, db_path: str) -> AsyncGenerator[str, None]:
    from mentat.db.repository import ApprovalRepository, ChatRepository

    chat_repo = ChatRepository(db_path)
    await chat_repo.save(role="user", content=message)

    intent = route(message)
    repo = ApprovalRepository(db_path)

    if intent == Intent.APPROVE_ALL:
        pending = await repo.list_pending()
        if pending:
            for req in pending:
                await repo.approve(req.id)
            reply = f"✅ {len(pending)}개 승인했습니다."
        else:
            reply = "대기 중인 승인 요청이 없습니다."
        yield reply
        await chat_repo.save(role="assistant", content=reply)

    elif intent == Intent.REJECT_ALL:
        pending = await repo.list_pending()
        if pending:
            for req in pending:
                await repo.reject(req.id)
            reply = f"❌ {len(pending)}개 거절했습니다."
        else:
            reply = "대기 중인 승인 요청이 없습니다."
        yield reply
        await chat_repo.save(role="assistant", content=reply)

    elif intent == Intent.LIST:
        pending = await repo.list_pending()
        if pending:
            lines = [f"대기 중 {len(pending)}개:"]
            for req in pending:
                name = req.data.get("name", req.id[:8])
                lines.append(f"  • {name}")
            reply = "\n".join(lines)
        else:
            reply = "대기 중인 승인 요청이 없습니다."
        yield reply
        await chat_repo.save(role="assistant", content=reply)

    elif intent == Intent.SCAN:
        reply = "프로젝트 스캔을 시작하려면 터미널에서 `mentat bootstrap`을 실행하세요."
        yield reply
        await chat_repo.save(role="assistant", content=reply)

    else:
        if os.environ.get("ANTHROPIC_API_KEY"):
            async for chunk in _claude_fallback(message, db_path):
                yield chunk
        else:
            reply = (
                "다음 명령어를 사용할 수 있습니다:\n"
                "  • **승인** — 대기 중인 모든 요청 승인\n"
                "  • **거절** — 대기 중인 모든 요청 거절\n"
                "  • **목록** — 대기 중인 요청 목록 확인\n"
                "  • **scan** — 프로젝트 스캔 안내"
            )
            yield reply
            await chat_repo.save(role="assistant", content=reply)


async def _claude_fallback(message: str, db_path: str) -> AsyncGenerator[str, None]:
    from mentat.db.repository import ChatRepository

    chat_repo = ChatRepository(db_path)
    try:
        import anthropic

        history = await chat_repo.history(limit=20)
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if m["role"] in ("user", "assistant")
        ]
        if not messages or messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": message})

        client = anthropic.Anthropic()
        full_reply: list[str] = []
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system="You are mentat, an autonomous PM assistant for solo developers. Be concise.",
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_reply.append(text)
                yield text

        await chat_repo.save(role="assistant", content="".join(full_reply))
    except Exception as e:
        reply = f"Claude API 오류: {e}"
        yield reply
        await chat_repo.save(role="assistant", content=reply)
