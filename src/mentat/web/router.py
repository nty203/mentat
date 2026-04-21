from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from mentat.db.repository import (
    ApprovalRepository,
    ChatRepository,
    ProjectRepository,
    RunRepository,
    SkillRepository,
    TokenRepository,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


def _db(request: Request) -> str:
    return str(request.app.state.db_path)


def _workers_dir() -> Path:
    install_dir = os.environ.get("MENTAT_INSTALL_DIR", "")
    if install_dir:
        return Path(install_dir) / "workers" / "templates"
    return Path(__file__).parent.parent.parent.parent / "workers" / "templates"


# ── main page ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    from mentat.core.llm import is_available, backend_name
    db_path = _db(request)
    pending = await ApprovalRepository(db_path).list_pending()
    projects = await ProjectRepository(db_path).list_all()
    history = await ChatRepository(db_path).history()
    skills = await SkillRepository(db_path).list_all()
    runs = await RunRepository(db_path).list_recent(limit=30)
    workers = _list_workers()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "pending": pending,
            "projects": projects,
            "history": history,
            "skills": skills,
            "runs": runs,
            "workers": workers,
            "available": is_available(),
            "backend": backend_name(),
        },
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


@router.get("/api/approvals/history", response_class=HTMLResponse)
async def approvals_history(request: Request) -> Any:
    all_approvals = await ApprovalRepository(_db(request)).list_all()
    return templates.TemplateResponse(
        request,
        "partials/approval_history.html",
        {"approvals": all_approvals},
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


@router.get("/api/browse/folder")
async def browse_folder() -> dict[str, str]:
    """Open a native OS folder picker and return the selected path."""
    import asyncio

    def _pick() -> str:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(title="프로젝트 폴더 선택")
            root.destroy()
            return folder or ""
        except Exception:
            return ""

    path = await asyncio.get_event_loop().run_in_executor(None, _pick)
    return {"path": path}


@router.post("/api/projects/add")
async def add_project(request: Request) -> Any:
    form = await request.form()
    raw_path = str(form.get("path", "")).strip()
    if not raw_path:
        return PlainTextResponse("경로를 입력하세요.", status_code=400)

    expanded = os.path.expandvars(os.path.expanduser(raw_path))
    p = Path(expanded)
    if not p.is_dir():
        return PlainTextResponse(f"폴더를 찾을 수 없습니다: {raw_path}", status_code=400)

    repo = ProjectRepository(_db(request))
    await repo.save(name=p.name, path=str(p), metadata={"source": "manual"})
    projects = await repo.list_all()
    return templates.TemplateResponse(
        request,
        "partials/project_list.html",
        {"projects": projects},
    )


# ── skills ───────────────────────────────────────────────────────────────────

@router.get("/api/skills", response_class=HTMLResponse)
async def skills_partial(request: Request) -> Any:
    skills = await SkillRepository(_db(request)).list_all()
    return templates.TemplateResponse(
        request,
        "partials/skills_list.html",
        {"skills": skills},
    )


@router.get("/api/skills/{skill_id}", response_class=HTMLResponse)
async def skill_detail(request: Request, skill_id: str) -> Any:
    skill = await SkillRepository(_db(request)).get(skill_id)
    return templates.TemplateResponse(
        request,
        "partials/skill_detail.html",
        {"skill": skill},
    )


# ── runs ─────────────────────────────────────────────────────────────────────

@router.get("/api/runs", response_class=HTMLResponse)
async def runs_partial(request: Request) -> Any:
    runs = await RunRepository(_db(request)).list_recent(limit=30)
    return templates.TemplateResponse(
        request,
        "partials/run_list.html",
        {"runs": runs},
    )


@router.get("/api/runs/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: str) -> Any:
    run = await RunRepository(_db(request)).get(run_id)
    return templates.TemplateResponse(
        request,
        "partials/run_detail.html",
        {"run": run},
    )


# ── workers ──────────────────────────────────────────────────────────────────

def _list_workers() -> list[dict[str, str]]:
    from mentat.core.worker_template import WorkerTemplateStore
    store = WorkerTemplateStore(str(_workers_dir()))
    result = []
    for name in sorted(store.list()):
        try:
            t = store.load(name)
            result.append({"name": name, "description": t.description, "body": t.body})
        except Exception:
            result.append({"name": name, "description": "", "body": ""})
    return result


@router.get("/api/workers", response_class=HTMLResponse)
async def workers_partial(request: Request) -> Any:
    return templates.TemplateResponse(
        request,
        "partials/workers_list.html",
        {"workers": _list_workers()},
    )


@router.get("/api/workers/{name}", response_class=HTMLResponse)
async def worker_detail(request: Request, name: str) -> Any:
    from mentat.core.worker_template import WorkerTemplateStore
    store = WorkerTemplateStore(str(_workers_dir()))
    try:
        worker = store.load(name)
        return templates.TemplateResponse(
            request,
            "partials/worker_detail.html",
            {"worker": {"name": worker.name, "description": worker.description, "body": worker.body}},
        )
    except FileNotFoundError:
        return HTMLResponse("<div class='p-4 text-red-400'>템플릿을 찾을 수 없습니다.</div>", status_code=404)


# ── settings ─────────────────────────────────────────────────────────────────

async def _settings_ctx(request: Request, saved: bool = False) -> dict[str, Any]:
    from mentat.config import get_model, get_token_limit, get_scan_interval
    from mentat.core.llm import backend_name, is_available
    token_stats = await TokenRepository(_db(request)).totals()
    return {
        "current_model": get_model(),
        "backend": backend_name(),
        "available": is_available(),
        "token_limit": get_token_limit(),
        "scan_interval": get_scan_interval(),
        "token_stats": token_stats,
        "saved": saved,
    }


@router.get("/api/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> Any:
    return templates.TemplateResponse(
        request, "partials/settings.html", await _settings_ctx(request)
    )


@router.post("/api/settings", response_class=HTMLResponse)
async def save_settings(request: Request) -> Any:
    from mentat.config import set_model, set_token_limit, set_scan_interval
    form = await request.form()
    set_model(str(form.get("model", "sonnet")).strip())
    try:
        set_token_limit(int(str(form.get("token_limit", "0")).strip()))
    except ValueError:
        pass
    try:
        interval = int(str(form.get("scan_interval", "60")).strip())
        if interval >= 1:
            set_scan_interval(interval)
    except ValueError:
        pass
    return templates.TemplateResponse(
        request, "partials/settings.html", await _settings_ctx(request, saved=True)
    )


@router.get("/api/status/connection", response_class=HTMLResponse)
async def connection_status(request: Request) -> Any:
    from mentat.core.llm import is_available, backend_name
    return templates.TemplateResponse(
        request,
        "partials/connection_badge.html",
        {"available": is_available(), "backend": backend_name()},
    )


@router.post("/api/test-connection")
async def test_connection() -> dict[str, Any]:
    import asyncio

    def _call() -> dict[str, Any]:
        try:
            from mentat.core.llm import make_client, get_configured_model
            client, models = make_client()
            model = get_configured_model(models)
            response = client.messages.create(
                model=model,
                max_tokens=5,
                messages=[{"role": "user", "content": "hi"}],
            )
            return {"ok": True, "model": response.model}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return await asyncio.get_event_loop().run_in_executor(None, _call)


@router.post("/api/token-usage/reset", response_class=HTMLResponse)
async def reset_token_usage(request: Request) -> Any:
    await TokenRepository(_db(request)).reset()
    return templates.TemplateResponse(
        request, "partials/settings.html", await _settings_ctx(request, saved=True)
    )


# ── chat ─────────────────────────────────────────────────────────────────────

@router.get("/api/chat/panel", response_class=HTMLResponse)
async def chat_panel(request: Request) -> Any:
    history = await ChatRepository(_db(request)).history()
    return templates.TemplateResponse(
        request,
        "partials/chat_panel.html",
        {"history": history},
    )


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
