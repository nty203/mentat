from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from mentat.db.repository import ApprovalRepository, ChatRepository, ProjectRepository

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


def _db(request: Request) -> str:
    return str(request.app.state.db_path)


# ── main page ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    db_path = _db(request)
    pending = await ApprovalRepository(db_path).list_pending()
    projects = await ProjectRepository(db_path).list_all()
    history = await ChatRepository(db_path).history()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"pending": pending, "projects": projects, "history": history},
    )


# ── approvals ────────────────────────────────────────────────────────────────

@router.get("/api/approvals", response_class=HTMLResponse)
async def approvals_partial(request: Request) -> Any:
    pending = await ApprovalRepository(_db(request)).list_pending()
    return templates.TemplateResponse(
        request,
        "partials/approvals.html",
        {"pending": pending},
    )


@router.post("/api/approvals/{request_id}/approve", response_class=HTMLResponse)
async def approve(request: Request, request_id: str) -> HTMLResponse:
    await ApprovalRepository(_db(request)).approve(request_id)
    return HTMLResponse("")


@router.post("/api/approvals/{request_id}/reject", response_class=HTMLResponse)
async def reject(request: Request, request_id: str) -> HTMLResponse:
    await ApprovalRepository(_db(request)).reject(request_id)
    return HTMLResponse("")


# ── projects ─────────────────────────────────────────────────────────────────

@router.get("/api/projects", response_class=HTMLResponse)
async def projects_partial(request: Request) -> Any:
    projects = await ProjectRepository(_db(request)).list_all()
    return templates.TemplateResponse(
        request,
        "partials/project_list.html",
        {"projects": projects},
    )


@router.get("/api/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: str) -> Any:
    project = await ProjectRepository(_db(request)).get(project_id)
    return templates.TemplateResponse(
        request,
        "partials/project_detail.html",
        {"project": project},
    )


# ── chat ─────────────────────────────────────────────────────────────────────

@router.post("/api/chat")
async def chat(request: Request) -> StreamingResponse:
    form = await request.form()
    message = str(form.get("message", "")).strip()
    if not message:
        return StreamingResponse(iter([]), media_type="text/event-stream")

    from mentat.web.chat import generate_response

    async def event_stream() -> Any:
        try:
            async for chunk in generate_response(message, _db(request)):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/api/chat/history")
async def chat_history(request: Request, limit: int = 100) -> list[dict[str, Any]]:
    return await ChatRepository(_db(request)).history(limit=limit)
