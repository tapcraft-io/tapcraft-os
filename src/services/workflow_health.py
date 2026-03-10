"""Workflow health monitoring service.

Queries Temporal for running workflows and detects unhealthy conditions:
- Activities retrying beyond threshold
- Workflows running longer than expected
- Workflows in a degraded state (some steps failed, still running)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from temporalio.api.enums.v1 import EventType
from temporalio.client import Client

from src.config.defaults import (
    LONG_RUNNING_WORKFLOW_THRESHOLD,
    STUCK_ACTIVITY_THRESHOLD,
)

LOGGER = logging.getLogger(__name__)
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")


async def get_workflow_health() -> dict[str, Any]:
    """Scan all running workflows and return health summary.

    Returns:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "running_count": int,
            "unhealthy_workflows": [...],
            "checked_at": str,
        }
    """
    client = await Client.connect(TEMPORAL_ADDRESS)
    now = datetime.now(tz=timezone.utc)

    running_count = 0
    unhealthy: list[dict[str, Any]] = []

    try:
        async for wf in client.list_workflows(query="ExecutionStatus = 'Running'"):
            running_count += 1

            issues: list[str] = []
            max_attempts = 0
            stuck_activity = None

            # Check if workflow has been running too long
            if wf.start_time:
                start = wf.start_time
                if hasattr(start, "ToDatetime"):
                    start = start.ToDatetime().replace(tzinfo=timezone.utc)
                elif start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                duration = now - start
                if duration > LONG_RUNNING_WORKFLOW_THRESHOLD:
                    hours = duration.total_seconds() / 3600
                    issues.append(
                        f"running for {hours:.1f}h (threshold: {LONG_RUNNING_WORKFLOW_THRESHOLD.total_seconds() / 3600:.0f}h)"
                    )

            # Fetch activity history to check for stuck retries
            try:
                handle = client.get_workflow_handle(wf.id)
                history = await handle.fetch_history()

                for event in history.events:
                    if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_STARTED:
                        attrs = event.activity_task_started_event_attributes
                        if attrs.attempt > max_attempts:
                            max_attempts = attrs.attempt
                            stuck_activity = None
                            # Find the scheduled event to get activity name
                            for prev in history.events:
                                if (
                                    prev.event_id == attrs.scheduled_event_id
                                    and prev.event_type
                                    == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED
                                ):
                                    stuck_activity = prev.activity_task_scheduled_event_attributes.activity_type.name
                                    break

                if max_attempts > STUCK_ACTIVITY_THRESHOLD:
                    msg = f"activity '{stuck_activity or '?'}' at {max_attempts} retries (threshold: {STUCK_ACTIVITY_THRESHOLD})"
                    issues.append(msg)

            except Exception as e:
                LOGGER.debug("Could not fetch history for %s: %s", wf.id, e)

            if issues:
                unhealthy.append(
                    {
                        "workflow_id": wf.id,
                        "workflow_type": wf.workflow_type,
                        "start_time": wf.start_time.isoformat()
                        if hasattr(wf.start_time, "isoformat")
                        else str(wf.start_time),
                        "max_activity_attempts": max_attempts,
                        "stuck_activity": stuck_activity,
                        "issues": issues,
                    }
                )

    except Exception as e:
        LOGGER.error("Failed to list workflows: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "running_count": 0,
            "unhealthy_workflows": [],
            "checked_at": now.isoformat(),
        }

    if unhealthy:
        # Any workflow with retries > threshold is "unhealthy", otherwise "degraded"
        has_stuck = any(w["max_activity_attempts"] > STUCK_ACTIVITY_THRESHOLD for w in unhealthy)
        status = "unhealthy" if has_stuck else "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "running_count": running_count,
        "unhealthy_workflows": unhealthy,
        "checked_at": now.isoformat(),
    }


async def terminate_stuck_workflows(
    max_attempts_threshold: int | None = None,
) -> dict[str, Any]:
    """Terminate workflows with activities stuck beyond the retry threshold.

    Returns summary of terminated workflows.
    """
    threshold = max_attempts_threshold or STUCK_ACTIVITY_THRESHOLD
    client = await Client.connect(TEMPORAL_ADDRESS)

    terminated: list[str] = []
    errors: list[str] = []

    try:
        async for wf in client.list_workflows(query="ExecutionStatus = 'Running'"):
            try:
                handle = client.get_workflow_handle(wf.id)
                history = await handle.fetch_history()

                max_attempts = 0
                for event in history.events:
                    if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_STARTED:
                        attrs = event.activity_task_started_event_attributes
                        max_attempts = max(max_attempts, attrs.attempt)

                if max_attempts > threshold:
                    await handle.terminate(
                        reason=f"Auto-terminated: activity stuck at {max_attempts} retries (threshold: {threshold})"
                    )
                    terminated.append(wf.id)
                    LOGGER.info(
                        "Terminated stuck workflow %s (max attempts: %d)",
                        wf.id,
                        max_attempts,
                    )

            except Exception as e:
                errors.append(f"{wf.id}: {e}")

    except Exception as e:
        return {"error": str(e), "terminated": [], "errors": []}

    return {
        "terminated": terminated,
        "terminated_count": len(terminated),
        "errors": errors,
    }
