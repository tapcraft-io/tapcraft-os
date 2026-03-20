"""API routes for Runs."""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.defaults import WORKFLOW_EXECUTION_TIMEOUT, WORKFLOW_RUN_TIMEOUT
from src.db.base import get_db
from src.models.schemas import (
    RunCreate,
    RunUpdate,
    RunResponse,
)
from src.services import crud

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    run_data: RunCreate,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new run."""
    run = await crud.create_run(
        db=db,
        workspace_id=workspace_id,
        workflow_id=run_data.workflow_id,
        input_config=run_data.input_config,
    )
    return run


@router.get("", response_model=List[RunResponse])
async def list_runs(
    workspace_id: int,
    workflow_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all runs in a workspace."""
    runs = await crud.list_runs(
        db=db, workspace_id=workspace_id, workflow_id=workflow_id, status=status
    )

    # Sync status from Temporal for any runs still marked as "running"
    stale_runs = [r for r in runs if r.status == "running" and r.temporal_workflow_id]
    if stale_runs:
        try:
            from temporalio.client import Client
            from temporalio.api.enums.v1 import WorkflowExecutionStatus

            temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
            client = await Client.connect(temporal_address)

            for run in stale_runs:
                try:
                    assert run.temporal_workflow_id is not None  # filtered above
                    handle = client.get_workflow_handle(run.temporal_workflow_id)
                    describe = await handle.describe()

                    new_status = "running"
                    wf_status = describe.status
                    if wf_status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_COMPLETED:
                        new_status = "succeeded"
                    elif wf_status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_CANCELED:
                        new_status = "cancelled"
                    elif wf_status in (
                        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_FAILED,
                        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TERMINATED,
                        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TIMED_OUT,
                    ):
                        new_status = "failed"

                    if new_status != run.status:
                        await crud.update_run(db=db, run_id=run.id, status=new_status)
                        run.status = new_status
                except Exception as e:
                    if "not found" in str(e).lower():
                        await crud.update_run(
                            db=db,
                            run_id=run.id,
                            status="failed",
                            error_excerpt="Workflow no longer exists in Temporal",
                        )
                        run.status = "failed"
                    else:
                        LOGGER.warning("Failed to sync status for run %s: %s", run.id, e)
        except Exception as e:
            LOGGER.warning("Failed to connect to Temporal for status sync: %s", e)

    return runs


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a run by ID."""
    run = await crud.get_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.patch("/{run_id}", response_model=RunResponse)
async def update_run(
    run_id: int,
    run_data: RunUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a run."""
    run = await crud.update_run(
        db=db,
        run_id=run_id,
        status=run_data.status,
        summary=run_data.summary,
        error_excerpt=run_data.error_excerpt,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# ============================================================================
# Retry & Cancel
# ============================================================================


class RetryRequest(BaseModel):
    input_config: Optional[Dict[str, Any]] = None


class RetryResponse(BaseModel):
    new_run_id: int
    temporal_workflow_id: str
    status: str


@router.post("/{run_id}/retry", response_model=RetryResponse)
async def retry_run(
    run_id: int,
    body: RetryRequest = RetryRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed or cancelled run by creating a new execution with the same config.

    Optionally override input_config in the request body.
    """
    import importlib
    from temporalio.client import Client

    run = await crud.get_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry a run with status '{run.status}'. Only failed or cancelled runs can be retried.",
        )

    workflow = await crud.get_workflow(db=db, workflow_id=run.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Original workflow not found")

    # Determine input config: use override if provided, else reuse original
    import json

    if body.input_config is not None:
        input_config = body.input_config
        input_config_str = json.dumps(input_config)
    else:
        input_config_str = run.input_config or "{}"
        try:
            input_config = json.loads(input_config_str)
        except (json.JSONDecodeError, TypeError):
            input_config = {}

    temporal_workflow_id = f"workflow-{workflow.slug}-{uuid.uuid4().hex[:8]}"

    # Create new run record
    new_run = await crud.create_run(
        db=db,
        workspace_id=run.workspace_id,
        workflow_id=run.workflow_id,
        input_config=input_config_str,
        temporal_workflow_id=temporal_workflow_id,
    )

    try:
        temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        client = await Client.connect(temporal_address)

        from src.services.workflow_resolver import resolve_workflow_class
        workflow_class = resolve_workflow_class(workflow.entrypoint_symbol)

        task_queue = os.getenv("TASK_QUEUE", "default")
        await client.start_workflow(
            workflow_class.run,
            input_config,
            id=temporal_workflow_id,
            task_queue=task_queue,
            execution_timeout=WORKFLOW_EXECUTION_TIMEOUT,
            run_timeout=WORKFLOW_RUN_TIMEOUT,
        )

        await crud.update_run(db=db, run_id=new_run.id, status="running")

        return RetryResponse(
            new_run_id=new_run.id,
            temporal_workflow_id=temporal_workflow_id,
            status="running",
        )

    except Exception as e:
        await crud.update_run(db=db, run_id=new_run.id, status="failed", error_excerpt=str(e)[:500])
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start retry workflow: {str(e)}",
        )


class CancelResponse(BaseModel):
    run_id: int
    status: str
    message: str


@router.post("/{run_id}/cancel", response_model=CancelResponse)
async def cancel_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running workflow execution.

    Sends a cancellation request to Temporal. If cancellation fails,
    falls back to termination.
    """
    from temporalio.client import Client

    run = await crud.get_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ("queued", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a run with status '{run.status}'. Only queued or running runs can be cancelled.",
        )

    if not run.temporal_workflow_id:
        # No Temporal execution — just mark as cancelled in DB
        await crud.update_run(
            db=db,
            run_id=run.id,
            status="cancelled",
            error_excerpt="Cancelled by user (no Temporal execution)",
        )
        return CancelResponse(
            run_id=run.id,
            status="cancelled",
            message="Run cancelled (was not yet submitted to Temporal)",
        )

    try:
        temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        client = await Client.connect(temporal_address)
        handle = client.get_workflow_handle(run.temporal_workflow_id)

        try:
            await handle.cancel()
        except Exception as cancel_err:
            LOGGER.warning(
                "Cancel request failed for run %d, attempting terminate: %s",
                run.id,
                cancel_err,
            )
            await handle.terminate(reason="Cancelled by user via Tapcraft API")

        await crud.update_run(
            db=db, run_id=run.id, status="cancelled", error_excerpt="Cancelled by user"
        )

        return CancelResponse(
            run_id=run.id,
            status="cancelled",
            message="Run cancelled successfully",
        )

    except Exception as e:
        LOGGER.error("Failed to cancel run %d: %s", run.id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel workflow: {str(e)}",
        )
