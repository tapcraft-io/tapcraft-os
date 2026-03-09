"""API routes for workflow execution."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import os

from src.config.defaults import WORKFLOW_EXECUTION_TIMEOUT, WORKFLOW_RUN_TIMEOUT
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

        if not module_path.startswith("workspace."):
            raise HTTPException(
                status_code=400,
                detail="Invalid module path: only workspace modules are allowed",
            )

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

        await client.start_workflow(
            workflow_class.run,
            request.input_config,
            id=temporal_workflow_id,
            task_queue=task_queue,
            execution_timeout=WORKFLOW_EXECUTION_TIMEOUT,
            run_timeout=WORKFLOW_RUN_TIMEOUT,
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
        raise HTTPException(status_code=500, detail=f"Failed to start workflow execution: {str(e)}")


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of a workflow run, including per-activity history."""
    from temporalio.client import Client

    run = await crud.get_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get workflow name for context
    workflow = (
        await crud.get_workflow(db=db, workflow_id=run.workflow_id) if run.workflow_id else None
    )
    workflow_name = workflow.name if workflow else f"Workflow {run.workflow_id}"

    base_response = {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "summary": run.summary,
        "error_excerpt": run.error_excerpt,
        "workflow_id": run.workflow_id,
        "workflow_name": workflow_name,
        "temporal_workflow_id": run.temporal_workflow_id,
        "input_config": run.input_config,
        "activity_history": [],
    }

    # If no temporal ID, return base response
    if not run.temporal_workflow_id:
        return base_response

    try:
        temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        client = await Client.connect(temporal_address)
        handle = client.get_workflow_handle(run.temporal_workflow_id)

        # Describe to get current status
        from temporalio.api.enums.v1 import WorkflowExecutionStatus

        describe = await handle.describe()

        status = "running"
        wf_status = describe.status
        if wf_status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_COMPLETED:
            status = "succeeded"
        elif wf_status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_CANCELED:
            status = "cancelled"
        elif wf_status in (
            WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_FAILED,
            WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TERMINATED,
            WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TIMED_OUT,
        ):
            status = "failed"

        # Update run in DB if status changed
        if status != run.status:
            await crud.update_run(db=db, run_id=run.id, status=status)

        base_response["status"] = status
        base_response["temporal_status"] = (
            WorkflowExecutionStatus.Name(int(wf_status))  # type: ignore[arg-type]
            if wf_status is not None
            else None
        )

        # Fetch activity execution history from Temporal
        activity_history = []
        try:
            from temporalio.api.enums.v1 import EventType

            history = await handle.fetch_history()
            activity_scheduled = {}  # event_id -> scheduled info

            for event in history.events:
                et = event.event_type

                if et == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
                    attrs = event.activity_task_scheduled_event_attributes
                    input_data = None
                    try:
                        import json as _json

                        if attrs.input and attrs.input.payloads:
                            input_data = _json.loads(attrs.input.payloads[0].data)
                    except Exception:
                        pass
                    activity_scheduled[event.event_id] = {
                        "activity_name": attrs.activity_type.name,
                        "scheduled_at": event.event_time.ToDatetime().isoformat()
                        if event.event_time
                        else None,
                        "scheduled_event_id": event.event_id,
                        "attempt": 1,
                        "input": input_data,
                        "output": None,
                        "retry_state": None,
                    }

                elif et == EventType.EVENT_TYPE_ACTIVITY_TASK_STARTED:
                    started_attrs = event.activity_task_started_event_attributes
                    sched_id = started_attrs.scheduled_event_id
                    if sched_id in activity_scheduled:
                        activity_scheduled[sched_id]["started_at"] = (
                            event.event_time.ToDatetime().isoformat() if event.event_time else None
                        )
                        activity_scheduled[sched_id]["attempt"] = started_attrs.attempt

                elif et == EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED:
                    completed_attrs = event.activity_task_completed_event_attributes
                    sched_id = completed_attrs.scheduled_event_id
                    if sched_id in activity_scheduled:
                        info = activity_scheduled[sched_id]
                        info["status"] = "completed"
                        info["ended_at"] = (
                            event.event_time.ToDatetime().isoformat() if event.event_time else None
                        )
                        output_data = None
                        try:
                            import json as _json

                            if completed_attrs.result and completed_attrs.result.payloads:
                                output_data = _json.loads(completed_attrs.result.payloads[0].data)
                        except Exception:
                            pass
                        info["output"] = output_data
                        activity_history.append(info)

                elif et == EventType.EVENT_TYPE_ACTIVITY_TASK_FAILED:
                    failed_attrs = event.activity_task_failed_event_attributes
                    sched_id = failed_attrs.scheduled_event_id
                    if sched_id in activity_scheduled:
                        info = activity_scheduled[sched_id]
                        info["status"] = "failed"
                        info["ended_at"] = (
                            event.event_time.ToDatetime().isoformat() if event.event_time else None
                        )
                        info["error"] = (
                            str(failed_attrs.failure.message) if failed_attrs.failure else None
                        )
                        info["error_type"] = (
                            str(failed_attrs.failure.server_failure_info)
                            if failed_attrs.failure and failed_attrs.failure.server_failure_info
                            else None
                        )
                        info["retry_state"] = (
                            str(failed_attrs.retry_state) if failed_attrs.retry_state else None
                        )
                        info["stack_trace"] = (
                            str(failed_attrs.failure.stack_trace)
                            if failed_attrs.failure and failed_attrs.failure.stack_trace
                            else None
                        )
                        activity_history.append(info)

                elif et == EventType.EVENT_TYPE_ACTIVITY_TASK_TIMED_OUT:
                    timeout_attrs = event.activity_task_timed_out_event_attributes
                    sched_id = timeout_attrs.scheduled_event_id
                    if sched_id in activity_scheduled:
                        info = activity_scheduled[sched_id]
                        info["status"] = "timed_out"
                        info["ended_at"] = (
                            event.event_time.ToDatetime().isoformat() if event.event_time else None
                        )
                        info["retry_state"] = (
                            str(timeout_attrs.retry_state) if timeout_attrs.retry_state else None
                        )
                        activity_history.append(info)

            # Add still-running activities (scheduled but not completed/failed)
            completed_ids = {a.get("scheduled_event_id") for a in activity_history}
            for sched_id, info in activity_scheduled.items():
                if sched_id not in completed_ids:
                    info["status"] = "running"
                    activity_history.append(info)

        except Exception:
            pass  # History fetch is best-effort

        base_response["activity_history"] = activity_history
        return base_response

    except Exception as e:
        base_response["error"] = f"Failed to query Temporal: {str(e)}"
        return base_response
