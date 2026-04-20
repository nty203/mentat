from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mentat.__init__ import __version__
from mentat.web.router import router as web_router

_STATIC_DIR = Path(__file__).parent / "static"

web_app = FastAPI(title="mentat", version=__version__)

if _STATIC_DIR.exists():
    web_app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

web_app.include_router(web_router)


def create_app(db_path: str) -> FastAPI:
    from mentat.core.introspection import router as introspection_router

    web_app.state.db_path = db_path
    web_app.include_router(introspection_router)
    return web_app
