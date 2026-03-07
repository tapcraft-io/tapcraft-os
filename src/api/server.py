"""FastAPI application exposing core Tapcraft OS endpoints."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Dict

from fastapi import Depends, FastAPI

# Import database initialization
from src.db.base import init_db

# Import auth
from src.api.auth import require_api_key, validate_key

# Import routers
from src.api.routers import activities, workflows, graphs, schedules, runs, execution, secrets, workspaces

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="Tapcraft OS API", version="0.1.0")

# Register routers — all require API key auth
app.include_router(activities.router, dependencies=[Depends(require_api_key)])
app.include_router(workflows.router, dependencies=[Depends(require_api_key)])
app.include_router(graphs.router, dependencies=[Depends(require_api_key)])
app.include_router(schedules.router, dependencies=[Depends(require_api_key)])
app.include_router(runs.router, dependencies=[Depends(require_api_key)])
app.include_router(execution.router, dependencies=[Depends(require_api_key)])
app.include_router(secrets.router, dependencies=[Depends(require_api_key)])
app.include_router(workspaces.router, dependencies=[Depends(require_api_key)])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()


class RuntimeConfig:
    def __init__(self) -> None:
        self.timezone = os.getenv("TZ_DEFAULT", "UTC")
        self.task_queue = os.getenv("TASK_QUEUE", "default")
        self.git_remote = os.getenv("GIT_REMOTE", "")
        self.git_branch = os.getenv("GIT_BRANCH", "main")

    def model_dump(self) -> Dict[str, Any]:
        temporal_addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

        return {
            "timezone": self.timezone,
            "task_queue": self.task_queue,
            "git_remote": self.git_remote,
            "git_branch": self.git_branch,
            "temporal": {
                "address": temporal_addr,
                "namespace": os.getenv("TEMPORAL_NAMESPACE", "default"),
            },
        }

    def update(self, payload: Dict[str, Any]) -> None:
        if "timezone" in payload:
            self.timezone = str(payload["timezone"])
        if "task_queue" in payload:
            self.task_queue = str(payload["task_queue"])
        if "git_remote" in payload:
            self.git_remote = str(payload["git_remote"])
        if "git_branch" in payload:
            self.git_branch = str(payload["git_branch"])


@lru_cache(maxsize=1)
def get_config() -> RuntimeConfig:
    return RuntimeConfig()


# --- Public endpoints (no auth) ---

@app.get("/health")
async def health() -> Dict[str, Any]:
    temporal_addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    temporal_connected = False
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")

    try:
        from temporalio.client import Client
        await Client.connect(temporal_addr)
        temporal_connected = True
    except Exception:
        pass

    return {
        "status": "ok",
        "temporal": {
            "connected": temporal_connected,
            "namespace": temporal_namespace,
        },
        "worker": {
            "active": True,
            "heartbeat_interval": 10,
        },
    }


@app.get("/auth/validate")
async def auth_validate_key(result: dict = Depends(validate_key)) -> dict:
    """UI calls this to check if a stored API key is still valid."""
    return result


# --- Protected endpoints ---

@app.get("/config", dependencies=[Depends(require_api_key)])
def read_config() -> Dict[str, Any]:
    return get_config().model_dump()


@app.put("/config", dependencies=[Depends(require_api_key)])
def update_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = get_config()
    config.update(payload)
    return config.model_dump()
