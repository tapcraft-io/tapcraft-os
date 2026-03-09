"""Execution tracker — syncs Temporal workflow executions back to Tapcraft's DB.

Runs as a background task in the worker. Periodically:
1. Lists recent Temporal workflow executions (completed, failed, running)
2. Matches them to registered DB workflows by workflow type name
3. Creates/updates Run records so the dashboard shows real data
4. Syncs schedule last_run_at / next_run_at from Temporal
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from temporalio.client import Client

LOGGER = logging.getLogger(__name__)
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

# How often to sync (seconds)
SYNC_INTERVAL = int(os.getenv("TAPCRAFT_SYNC_INTERVAL", "30"))


def _parse_temporal_time(t) -> datetime | None:
    """Normalize a Temporal timestamp to a timezone-aware datetime."""
    if t is None:
        return None
    if hasattr(t, 'ToDatetime'):
        return t.ToDatetime().replace(tzinfo=timezone.utc)
    if isinstance(t, datetime):
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    return None


async def _sync_once(client: Client) -> None:
    """Run one sync cycle."""
    from sqlalchemy import select
    from src.db.base import AsyncSessionLocal
    from src.db.models import Run, Schedule, Workflow

    async with AsyncSessionLocal() as db:
        # Load all workflows — build a map from entrypoint class name to workflow
        wf_result = await db.execute(select(Workflow))
        workflows = list(wf_result.scalars().all())

        if not workflows:
            return

        # Map: workflow type name (class name) → Workflow DB record
        # entrypoint_symbol like "tapcraft.workflows.signal_pipeline.SignalPipelineWorkflow"
        # Temporal workflow type is just the class name: "SignalPipelineWorkflow"
        type_to_workflow: dict[str, any] = {}
        for wf in workflows:
            class_name = wf.entrypoint_symbol.rsplit(".", 1)[-1] if "." in wf.entrypoint_symbol else wf.entrypoint_symbol
            type_to_workflow[class_name] = wf

        # Get existing temporal_workflow_ids we've already tracked
        existing_result = await db.execute(
            select(Run.temporal_workflow_id).where(
                Run.temporal_workflow_id.isnot(None)
            )
        )
        known_wf_ids = {r for r in existing_result.scalars().all()}

        # Query Temporal for workflow executions
        new_runs = 0
        updated_runs = 0

        for status_query, run_status in [
            ("ExecutionStatus = 'Running'", "running"),
            ("ExecutionStatus = 'Completed'", "succeeded"),
            ("ExecutionStatus = 'Failed'", "failed"),
        ]:
            try:
                async for wf in client.list_workflows(query=status_query):
                    # Match workflow type to a registered DB workflow
                    db_workflow = type_to_workflow.get(wf.workflow_type)
                    if not db_workflow:
                        continue

                    start_time = _parse_temporal_time(wf.start_time)
                    close_time = _parse_temporal_time(wf.close_time)

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
                        workspace_id=db_workflow.workspace_id,
                        workflow_id=db_workflow.id,
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
        sched_result = await db.execute(
            select(Schedule).where(Schedule.enabled == True)  # noqa: E712
        )
        schedules = list(sched_result.scalars().all())

        for schedule in schedules:
            try:
                from src.services.schedule_service import describe_temporal_schedule
                info = await describe_temporal_schedule(schedule.id)
                if not info:
                    continue

                next_times = info.get("next_action_times", [])
                if next_times:
                    schedule.next_run_at = datetime.fromisoformat(next_times[0])

                recent = info.get("recent_actions", [])
                if recent:
                    last_action = recent[-1]
                    started = last_action.get("started_at") or last_action.get("scheduled_at")
                    if started:
                        schedule.last_run_at = datetime.fromisoformat(started)

            except Exception as e:
                LOGGER.debug("Could not describe schedule %d: %s", schedule.id, e)

        if new_runs or updated_runs:
            await db.commit()
            LOGGER.info(
                "Execution tracker: %d new runs, %d updated",
                new_runs, updated_runs,
            )
        else:
            await db.commit()  # commit schedule time updates


async def run_execution_tracker(shutdown_event: asyncio.Event) -> None:
    """Background loop that syncs Temporal executions to the DB."""
    LOGGER.info("Execution tracker started (interval: %ds)", SYNC_INTERVAL)

    client = await Client.connect(TEMPORAL_ADDRESS)

    while not shutdown_event.is_set():
        try:
            await _sync_once(client)
        except Exception as e:
            LOGGER.error("Execution tracker error: %s", e)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=SYNC_INTERVAL)
            break
        except asyncio.TimeoutError:
            pass

    LOGGER.info("Execution tracker stopped")
