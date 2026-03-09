"""Background service that syncs Temporal execution state into the Tapcraft DB.

The ``ExecutionTracker`` runs as a long-lived asyncio task inside the worker
process.  Every polling interval it:

1. Queries Temporal for recently completed workflow executions.
2. Matches them to registered Tapcraft workflows by workflow type (class name).
3. Creates Run records for new executions not yet tracked.
4. Updates the status of in-progress Run records whose Temporal executions
   have finished.
5. Syncs ``last_run_at`` / ``next_run_at`` on Schedule records from Temporal.

This keeps the Tapcraft dashboard accurate without requiring the user's
workflow code to call back into Tapcraft.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from temporalio.api.enums.v1 import WorkflowExecutionStatus
from temporalio.client import Client

from src.db.base import AsyncSessionLocal
from src.services import crud

LOGGER = logging.getLogger(__name__)

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
POLL_INTERVAL_SECONDS = int(os.getenv("EXECUTION_TRACKER_INTERVAL", "30"))


def _temporal_status_to_run_status(
    status: WorkflowExecutionStatus,
) -> str:
    """Map a Temporal execution status to a Tapcraft run status string."""
    _MAP = {
        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_RUNNING: "running",
        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_COMPLETED: "succeeded",
        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_FAILED: "failed",
        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_CANCELED: "cancelled",
        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TERMINATED: "failed",
        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_CONTINUED_AS_NEW: "succeeded",
        WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TIMED_OUT: "failed",
    }
    return _MAP.get(status, "failed")


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------


async def _build_workflow_type_index(
    db: "AsyncSession",  # noqa: F821
) -> Dict[str, Any]:
    """Build a mapping from Temporal workflow type name to DB Workflow object.

    We inspect ``entrypoint_symbol`` (which is the class name for imported
    workflows) to create this index.  For non-imported workflows the
    entrypoint is a fully-qualified dotted path — we extract the last
    segment (the class name) for matching.
    """
    from sqlalchemy import select
    from src.db.models import Workflow

    result = await db.execute(select(Workflow))
    workflows = list(result.scalars().all())

    index: Dict[str, Any] = {}
    for wf in workflows:
        # The entrypoint_symbol is either a bare class name (imported) or
        # a dotted path like ``workspace.workspace_1.workflows.foo.MyWorkflow``
        class_name = wf.entrypoint_symbol.rsplit(".", 1)[-1]
        index[class_name] = wf

    return index


async def sync_completed_executions(client: Client) -> Dict[str, int]:
    """Scan for recently completed Temporal executions and create/update Runs.

    Returns a dict with counts of ``created`` and ``updated`` Run records.
    """
    stats = {"created": 0, "updated": 0, "errors": 0}

    async with AsyncSessionLocal() as db:
        type_index = await _build_workflow_type_index(db)
        if not type_index:
            return stats

        # Collect existing tracked temporal_workflow_ids
        all_runs = []
        for wf in type_index.values():
            runs = await crud.list_runs(
                db=db, workspace_id=wf.workspace_id, workflow_id=wf.id
            )
            all_runs.extend(runs)

        tracked_ids: Dict[str, Any] = {}
        for run in all_runs:
            if run.temporal_workflow_id:
                tracked_ids[run.temporal_workflow_id] = run

        # Query Temporal for completed and running workflows
        queries = [
            "ExecutionStatus = 'Completed'",
            "ExecutionStatus = 'Failed'",
            "ExecutionStatus = 'Canceled'",
            "ExecutionStatus = 'Terminated'",
            "ExecutionStatus = 'TimedOut'",
            "ExecutionStatus = 'Running'",
        ]

        for query in queries:
            count = 0
            try:
                async for wf in client.list_workflows(query=query):
                    count += 1
                    # Limit per query to avoid overwhelming the DB
                    if count > 200:
                        break

                    wf_type = wf.workflow_type
                    if not wf_type or wf_type not in type_index:
                        continue

                    db_workflow = type_index[wf_type]
                    new_status = _temporal_status_to_run_status(wf.status)

                    if wf.id in tracked_ids:
                        # Update existing run if status changed
                        existing_run = tracked_ids[wf.id]
                        if existing_run.status in ("queued", "running") and new_status != existing_run.status:
                            try:
                                await crud.update_run(
                                    db=db,
                                    run_id=existing_run.id,
                                    status=new_status,
                                )
                                stats["updated"] += 1
                            except Exception as exc:
                                LOGGER.debug(
                                    "Failed to update run %d: %s",
                                    existing_run.id,
                                    exc,
                                )
                                stats["errors"] += 1
                    else:
                        # Create a new Run record for this execution
                        start_time: Optional[datetime] = None
                        if wf.start_time:
                            start_time = wf.start_time
                            if start_time.tzinfo is None:
                                start_time = start_time.replace(tzinfo=timezone.utc)

                        close_time: Optional[datetime] = None
                        if wf.close_time:
                            close_time = wf.close_time
                            if close_time.tzinfo is None:
                                close_time = close_time.replace(tzinfo=timezone.utc)

                        try:
                            run = await crud.create_run(
                                db=db,
                                workspace_id=db_workflow.workspace_id,
                                workflow_id=db_workflow.id,
                                input_config="{}",
                                temporal_workflow_id=wf.id,
                                temporal_run_id=wf.run_id if hasattr(wf, "run_id") else None,
                            )

                            run.status = new_status
                            run.started_at = start_time
                            run.ended_at = close_time
                            await db.commit()
                            await db.refresh(run)

                            tracked_ids[wf.id] = run
                            stats["created"] += 1
                        except Exception as exc:
                            LOGGER.debug(
                                "Failed to create run for %s: %s", wf.id, exc
                            )
                            stats["errors"] += 1

            except Exception as exc:
                LOGGER.warning(
                    "Failed to list workflows with query '%s': %s", query, exc
                )

    return stats


async def sync_schedule_timing(client: Client) -> int:
    """Sync ``last_run_at`` and ``next_run_at`` on Schedule records from Temporal.

    Returns the number of schedules updated.
    """
    updated = 0

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from src.db.models import Schedule

        result = await db.execute(select(Schedule))
        schedules = list(result.scalars().all())

        if not schedules:
            return 0

        for sched in schedules:
            try:
                from src.services.schedule_service import describe_temporal_schedule

                info = await describe_temporal_schedule(sched.id)
                if not info:
                    continue

                changed = False

                # Sync next run time
                next_times = info.get("next_action_times", [])
                if next_times:
                    try:
                        next_dt = datetime.fromisoformat(next_times[0])
                        if sched.next_run_at != next_dt:
                            sched.next_run_at = next_dt
                            changed = True
                    except (ValueError, TypeError):
                        pass

                # Sync last run time from recent actions
                recent = info.get("recent_actions", [])
                if recent:
                    last_action = recent[-1]
                    started = last_action.get("started_at")
                    if started:
                        try:
                            last_dt = datetime.fromisoformat(started)
                            if sched.last_run_at != last_dt:
                                sched.last_run_at = last_dt
                                changed = True
                        except (ValueError, TypeError):
                            pass

                if changed:
                    await db.commit()
                    await db.refresh(sched)
                    updated += 1

            except Exception as exc:
                LOGGER.debug(
                    "Failed to sync timing for schedule %d: %s", sched.id, exc
                )

    return updated


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------


async def run_execution_tracker(shutdown_event: asyncio.Event) -> None:
    """Main loop for the execution tracker background task.

    Runs until ``shutdown_event`` is set.  Each iteration connects to
    Temporal, syncs executions, and syncs schedule timing.

    Args:
        shutdown_event: Set this event to stop the tracker gracefully.
    """
    LOGGER.info(
        "Execution tracker starting (poll interval: %ds)", POLL_INTERVAL_SECONDS
    )

    while not shutdown_event.is_set():
        try:
            client = await Client.connect(TEMPORAL_ADDRESS)

            exec_stats = await sync_completed_executions(client)
            if exec_stats["created"] or exec_stats["updated"]:
                LOGGER.info(
                    "Execution sync: %d runs created, %d updated, %d errors",
                    exec_stats["created"],
                    exec_stats["updated"],
                    exec_stats["errors"],
                )

            sched_updated = await sync_schedule_timing(client)
            if sched_updated:
                LOGGER.info("Schedule timing sync: %d schedules updated", sched_updated)

        except Exception as exc:
            LOGGER.warning("Execution tracker cycle failed: %s", exc)

        # Wait for the poll interval or until shutdown is requested
        try:
            await asyncio.wait_for(
                shutdown_event.wait(), timeout=POLL_INTERVAL_SECONDS
            )
            # If we get here, shutdown was requested
            break
        except asyncio.TimeoutError:
            # Normal — poll interval elapsed, loop again
            continue

    LOGGER.info("Execution tracker stopped")
