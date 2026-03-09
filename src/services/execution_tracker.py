"""Execution tracker — syncs Temporal workflow executions back to Tapcraft's DB.

Runs as a background task in the worker. Periodically:
1. Lists recent Temporal workflow executions (completed, failed, running)
2. Matches schedule-triggered executions to DB schedules → workflows
3. Creates/updates Run records so the dashboard shows real data
4. Syncs schedule last_run_at / next_run_at from Temporal
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone

from temporalio.client import Client

LOGGER = logging.getLogger(__name__)
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

# How often to sync (seconds)
SYNC_INTERVAL = int(os.getenv("TAPCRAFT_SYNC_INTERVAL", "30"))

# Pattern for schedule-triggered workflow IDs: scheduled-tapcraft-schedule-{db_id}-{timestamp}
_SCHEDULE_WF_RE = re.compile(r"^scheduled-tapcraft-schedule-(\d+)-(.+)$")


async def _sync_once(client: Client) -> None:
    """Run one sync cycle."""
    from sqlalchemy import select
    from src.db.base import AsyncSessionLocal
    from src.db.models import Run, Schedule, Workflow
    from src.services.schedule_service import describe_temporal_schedule

    async with AsyncSessionLocal() as db:
        # Load all schedules with their workflows
        sched_result = await db.execute(
            select(Schedule).where(Schedule.enabled == True)  # noqa: E712
        )
        schedules = {s.id: s for s in sched_result.scalars().all()}

        if not schedules:
            return

        # Load workflows for these schedules
        wf_ids = {s.workflow_id for s in schedules.values()}
        wf_result = await db.execute(select(Workflow).where(Workflow.id.in_(wf_ids)))
        workflows = {w.id: w for w in wf_result.scalars().all()}

        # Get existing temporal_workflow_ids we've already tracked
        existing_result = await db.execute(
            select(Run.temporal_workflow_id).where(
                Run.temporal_workflow_id.isnot(None)
            )
        )
        known_wf_ids = {r for r in existing_result.scalars().all()}

        # Query Temporal for recent workflow executions matching schedule pattern
        new_runs = 0
        updated_runs = 0

        for status_query in [
            "ExecutionStatus = 'Completed'",
            "ExecutionStatus = 'Failed'",
            "ExecutionStatus = 'Running'",
        ]:
            try:
                async for wf in client.list_workflows(query=status_query):
                    # Check if this is a schedule-triggered execution
                    match = _SCHEDULE_WF_RE.match(wf.id)
                    if not match:
                        continue

                    schedule_db_id = int(match.group(1))
                    schedule = schedules.get(schedule_db_id)
                    if not schedule:
                        continue

                    workflow = workflows.get(schedule.workflow_id)
                    if not workflow:
                        continue

                    # Determine status
                    if "Completed" in status_query:
                        run_status = "succeeded"
                    elif "Failed" in status_query:
                        run_status = "failed"
                    else:
                        run_status = "running"

                    # Parse times
                    start_time = None
                    if wf.start_time:
                        start_time = wf.start_time
                        if hasattr(start_time, 'ToDatetime'):
                            start_time = start_time.ToDatetime().replace(tzinfo=timezone.utc)
                        elif start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=timezone.utc)

                    close_time = None
                    if wf.close_time:
                        close_time = wf.close_time
                        if hasattr(close_time, 'ToDatetime'):
                            close_time = close_time.ToDatetime().replace(tzinfo=timezone.utc)
                        elif close_time.tzinfo is None:
                            close_time = close_time.replace(tzinfo=timezone.utc)

                    if wf.id in known_wf_ids:
                        # Update existing run if status changed
                        existing_run_result = await db.execute(
                            select(Run).where(Run.temporal_workflow_id == wf.id)
                        )
                        existing_run = existing_run_result.scalars().first()
                        if existing_run and existing_run.status != run_status:
                            existing_run.status = run_status
                            if run_status == "running" and not existing_run.started_at:
                                existing_run.started_at = start_time
                            if run_status in ("succeeded", "failed") and not existing_run.ended_at:
                                existing_run.ended_at = close_time
                            updated_runs += 1
                        continue

                    # Create new Run record
                    run = Run(
                        workspace_id=schedule.workspace_id,
                        workflow_id=schedule.workflow_id,
                        status=run_status,
                        started_at=start_time,
                        ended_at=close_time,
                        input_config="{}",
                        temporal_workflow_id=wf.id,
                    )
                    db.add(run)
                    known_wf_ids.add(wf.id)
                    new_runs += 1

            except Exception as e:
                LOGGER.warning("Error querying Temporal for %s: %s", status_query, e)

        # Sync schedule last_run_at and next_run_at
        for sched_id, schedule in schedules.items():
            try:
                info = await describe_temporal_schedule(sched_id)
                if not info:
                    continue

                # Update next_run_at
                next_times = info.get("next_action_times", [])
                if next_times:
                    schedule.next_run_at = datetime.fromisoformat(next_times[0])

                # Update last_run_at from recent_actions
                recent = info.get("recent_actions", [])
                if recent:
                    last_action = recent[-1]
                    started = last_action.get("started_at") or last_action.get("scheduled_at")
                    if started:
                        schedule.last_run_at = datetime.fromisoformat(started)

            except Exception as e:
                LOGGER.debug("Could not describe schedule %d: %s", sched_id, e)

        if new_runs or updated_runs:
            await db.commit()
            LOGGER.info(
                "Execution tracker: %d new runs, %d updated runs",
                new_runs, updated_runs,
            )


async def run_execution_tracker(shutdown_event: asyncio.Event) -> None:
    """Background loop that syncs Temporal executions to the DB."""
    LOGGER.info("Execution tracker started (interval: %ds)", SYNC_INTERVAL)

    client = await Client.connect(TEMPORAL_ADDRESS)

    while not shutdown_event.is_set():
        try:
            await _sync_once(client)
        except Exception as e:
            LOGGER.error("Execution tracker error: %s", e)

        # Wait for interval or shutdown
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=SYNC_INTERVAL)
            break  # shutdown requested
        except asyncio.TimeoutError:
            pass  # normal — interval elapsed, run again

    LOGGER.info("Execution tracker stopped")
