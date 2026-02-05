"""API routes for workflow execution."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import os

from src.db.base import get_db
from src.services import crud

router = APIRouter(prefix="/execution", tags=["execution"])


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""

    workflow_id: int
    input_config: Dict[str, Any] = {}


class ExecuteWorkflowResponse(BaseModel):
    """Response from workflow execution."""

    run_id: int
    workflow_id: int
    temporal_workflow_id: str
    status: str


@router.post("/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(
    workflow_id: int,
    request: ExecuteWorkflowRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a workflow by starting a Temporal workflow execution.

    Creates a Run record and starts the workflow on Temporal.
    """
    import uuid
    from temporalio.client import Client

    # Get workflow
    workflow = await crud.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create run record
    temporal_workflow_id = f"workflow-{workflow.slug}-{uuid.uuid4().hex[:8]}"

    run = await crud.create_run(
        db=db,
        workspace_id=workflow.workspace_id,
        workflow_id=workflow.id,
        input_config=str(request.input_config),
        temporal_workflow_id=temporal_workflow_id,
    )

    try:
        # Connect to Temporal
        temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        client = await Client.connect(temporal_address)

        # Parse entrypoint to get workflow class
        # Format: workspace.workspace_N.workflows.module.ClassName
        module_path, class_name = workflow.entrypoint_symbol.rsplit(".", 1)

        # Import the workflow class
        import importlib

        try:
            module = importlib.import_module(module_path)
            workflow_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to import workflow {workflow.entrypoint_symbol}: {str(e)}",
            )

        # Start workflow execution
        task_queue = os.getenv("TASK_QUEUE", "default")

        handle = await client.start_workflow(
            workflow_class.run,
            request.input_config,
            id=temporal_workflow_id,
            task_queue=task_queue,
        )

        # Update run with temporal run ID
        await crud.update_run(
            db=db,
            run_id=run.id,
            status="running",
        )

        return ExecuteWorkflowResponse(
            run_id=run.id,
            workflow_id=workflow.id,
            temporal_workflow_id=temporal_workflow_id,
            status="running",
        )

    except Exception as e:
        # Update run as failed
        await crud.update_run(
            db=db,
            run_id=run.id,
            status="failed",
            error_excerpt=str(e)[:500],
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to start workflow execution: {str(e)}"
        )


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of a workflow run."""
    from temporalio.client import Client

    run = await crud.get_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # If run is already finished, return status from DB
    if run.status in ("succeeded", "failed"):
        return {
            "run_id": run.id,
            "status": run.status,
            "started_at": run.started_at,
            "ended_at": run.ended_at,
            "summary": run.summary,
            "error_excerpt": run.error_excerpt,
        }

    # Query Temporal for current status
    if run.temporal_workflow_id:
        try:
            temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
            client = await Client.connect(temporal_address)

            handle = client.get_workflow_handle(run.temporal_workflow_id)

            # Try to get the result (non-blocking describe)
            describe = await handle.describe()

            status = "running"
            if describe.status.name == "COMPLETED":
                status = "succeeded"
            elif describe.status.name in ("FAILED", "TERMINATED", "TIMED_OUT"):
                status = "failed"

            # Update run in DB if status changed
            if status != run.status:
                await crud.update_run(db=db, run_id=run.id, status=status)

            return {
                "run_id": run.id,
                "status": status,
                "started_at": run.started_at,
                "temporal_status": describe.status.name,
            }

        except Exception as e:
            return {
                "run_id": run.id,
                "status": run.status,
                "error": f"Failed to query Temporal: {str(e)}",
            }

    return {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.started_at,
    }
