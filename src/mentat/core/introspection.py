from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from mentat.__init__ import __version__

app = FastAPI(title="mentat introspection", version=__version__)

# In-memory state — populated by agents at runtime
_agents: list[dict[str, Any]] = []
_approvals: list[dict[str, Any]] = []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/agents")
async def agents() -> list[dict[str, Any]]:
    return _agents


@app.get("/approvals")
async def approvals() -> list[dict[str, Any]]:
    return _approvals
