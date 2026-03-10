"""API routes for workflow health monitoring and guardrails."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.config.defaults import (
    DEFAULT_ACTIVITY_MAX_ATTEMPTS,
    DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
    MAX_ACTIVITY_RETRY_ATTEMPTS,
    STUCK_ACTIVITY_THRESHOLD,
    LONG_RUNNING_WORKFLOW_THRESHOLD,
    WORKFLOW_EXECUTION_TIMEOUT,
    WORKFLOW_RUN_TIMEOUT,
)
from src.services.workflow_health import get_workflow_health, terminate_stuck_workflows

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/workflows")
async def workflow_health() -> Dict[str, Any]:
    """Get health status of all running workflows.

    Returns workflow health summary including:
    - Overall status (healthy/degraded/unhealthy)
    - Count of running workflows
    - List of unhealthy workflows with specific issues
    """
    return await get_workflow_health()


class TerminateResponse(BaseModel):
    terminated: list[str]
    terminated_count: int
    errors: list[str]


@router.post("/workflows/terminate-stuck", response_model=TerminateResponse)
async def terminate_stuck(
    threshold: Optional[int] = Query(
        None,
        description="Override retry threshold (default from platform config)",
    ),
) -> Dict[str, Any]:
    """Terminate all workflows with activities stuck beyond the retry threshold.

    Use this to clean up runaway workflows that are burning worker resources.
    """
    return await terminate_stuck_workflows(max_attempts_threshold=threshold)


@router.get("/config")
async def platform_defaults() -> Dict[str, Any]:
    """Show current platform guardrail configuration."""
    return {
        "workflow_execution_timeout_hours": WORKFLOW_EXECUTION_TIMEOUT.total_seconds() / 3600,
        "workflow_run_timeout_hours": WORKFLOW_RUN_TIMEOUT.total_seconds() / 3600,
        "default_activity_max_attempts": DEFAULT_ACTIVITY_MAX_ATTEMPTS,
        "default_activity_timeout_seconds": DEFAULT_ACTIVITY_TIMEOUT_SECONDS,
        "max_activity_retry_attempts": MAX_ACTIVITY_RETRY_ATTEMPTS,
        "stuck_activity_threshold": STUCK_ACTIVITY_THRESHOLD,
        "long_running_workflow_threshold_hours": LONG_RUNNING_WORKFLOW_THRESHOLD.total_seconds() / 3600,
    }
