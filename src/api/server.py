"""FastAPI application exposing core Tapcraft OS endpoints."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request

# Import database initialization
from src.db.base import init_db

# Import auth
from src.api.auth import require_api_key, validate_key

# Import routers
from src.api.routers import activities, workflows, graphs, schedules, runs, execution, secrets, workspaces, webhooks, oauth

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
app.include_router(webhooks.router, dependencies=[Depends(require_api_key)])
app.include_router(oauth.router, dependencies=[Depends(require_api_key)])


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


# --- Public webhook inbound endpoint (no auth — verified by HMAC secret) ---

@app.post("/hooks/{path:path}")
async def webhook_inbound(path: str, request: Request) -> Dict[str, Any]:
    """Receive an inbound webhook and trigger the associated workflow."""
    import hashlib
    import hmac
    import json
    import uuid

    import importlib
    from temporalio.client import Client

    from src.db.base import get_db_session
    from src.services import crud

    body = await request.body()

    async with get_db_session() as db:
        webhook = await crud.get_webhook_by_path(db=db, path=path)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        if not webhook.enabled:
            raise HTTPException(status_code=403, detail="Webhook is disabled")

        # Verify HMAC signature if webhook has a secret
        if webhook.secret:
            signature = request.headers.get("X-Webhook-Signature", "")
            expected = hmac.new(
                webhook.secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        # Get the workflow
        workflow = await crud.get_workflow(db=db, workflow_id=webhook.workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Parse body as input config
        try:
            input_config = json.loads(body) if body else {}
        except (json.JSONDecodeError, ValueError):
            input_config = {"raw_body": body.decode("utf-8", errors="replace")}

        # Add webhook metadata
        input_config["_webhook"] = {
            "path": path,
            "method": request.method,
            "headers": dict(request.headers),
            "webhook_id": webhook.id,
        }

        # Create run record
        temporal_workflow_id = f"webhook-{webhook.path}-{uuid.uuid4().hex[:8]}"

        run = await crud.create_run(
            db=db,
            workspace_id=webhook.workspace_id,
            workflow_id=webhook.workflow_id,
            input_config=json.dumps(input_config),
            temporal_workflow_id=temporal_workflow_id,
        )

        # Increment webhook trigger count
        await crud.increment_webhook_trigger(db=db, webhook_id=webhook.id)

        # Start Temporal workflow
        try:
            temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
            client = await Client.connect(temporal_address)

            module_path, class_name = workflow.entrypoint_symbol.rsplit(".", 1)
            module = importlib.import_module(module_path)
            workflow_class = getattr(module, class_name)

            task_queue = os.getenv("TASK_QUEUE", "default")
            await client.start_workflow(
                workflow_class.run,
                input_config,
                id=temporal_workflow_id,
                task_queue=task_queue,
            )

            await crud.update_run(db=db, run_id=run.id, status="running")

            return {
                "accepted": True,
                "run_id": run.id,
                "temporal_workflow_id": temporal_workflow_id,
            }

        except Exception as e:
            await crud.update_run(
                db=db, run_id=run.id, status="failed", error_excerpt=str(e)[:500]
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to start workflow: {str(e)}"
            )


# --- Protected endpoints ---

@app.get("/config", dependencies=[Depends(require_api_key)])
def read_config() -> Dict[str, Any]:
    return get_config().model_dump()


@app.put("/config", dependencies=[Depends(require_api_key)])
def update_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = get_config()
    config.update(payload)
    return config.model_dump()
