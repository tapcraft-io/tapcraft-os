"""Programmatic schedule setup for built-in workflows.

Creates or updates Temporal schedules for workflows that run on a fixed cron.
Run this script after the worker has started to ensure workflows are registered.

Usage:
    python -m src.setup_schedules
"""

import asyncio
import logging
import os

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleState,
)

from src.workflows.signal_pipeline import SignalPipelineWorkflow

LOGGER = logging.getLogger(__name__)

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TASK_QUEUE = os.getenv("TASK_QUEUE", "default")

# ---------------------------------------------------------------------------
# Schedule definitions
# ---------------------------------------------------------------------------
SCHEDULES = [
    {
        "id": "signal-processor",
        "workflow": "SignalPipelineWorkflow",
        "cron": "*/30 * * * *",
    },
]

# Map workflow name -> class for action binding
_WORKFLOW_MAP = {
    "SignalPipelineWorkflow": SignalPipelineWorkflow,
}


async def ensure_schedules() -> int:
    """Create or update all built-in schedules. Returns count of created/updated."""
    client = await Client.connect(TEMPORAL_ADDRESS)
    count = 0

    for spec in SCHEDULES:
        schedule_id = spec["id"]
        workflow_cls = _WORKFLOW_MAP.get(spec["workflow"])
        if workflow_cls is None:
            LOGGER.error(
                "Unknown workflow %s for schedule %s — skipping", spec["workflow"], schedule_id
            )
            continue

        cron = spec["cron"]

        schedule = Schedule(
            action=ScheduleActionStartWorkflow(
                workflow_cls.run,
                id=f"scheduled-{schedule_id}-{{{{.ScheduledTime}}}}",
                task_queue=TASK_QUEUE,
            ),
            spec=ScheduleSpec(cron_expressions=[cron]),
            state=ScheduleState(paused=False),
        )

        # Try to create; if it already exists, update it
        try:
            await client.create_schedule(schedule_id, schedule)
            LOGGER.info(
                "Created schedule %s (cron=%s, workflow=%s)", schedule_id, cron, spec["workflow"]
            )
            count += 1
        except Exception as e:
            if "already exists" in str(e).lower():
                try:
                    handle = client.get_schedule_handle(schedule_id)

                    async def _updater(existing: Schedule) -> Schedule:
                        existing.action = schedule.action
                        existing.spec = schedule.spec
                        existing.state = schedule.state
                        return existing

                    await handle.update(_updater)
                    LOGGER.info(
                        "Updated schedule %s (cron=%s, workflow=%s)",
                        schedule_id,
                        cron,
                        spec["workflow"],
                    )
                    count += 1
                except Exception as ue:
                    LOGGER.error("Failed to update schedule %s: %s", schedule_id, ue)
            else:
                LOGGER.error("Failed to create schedule %s: %s", schedule_id, e)

    return count


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    count = await ensure_schedules()
    LOGGER.info("Setup complete: %d schedule(s) created/updated", count)


if __name__ == "__main__":
    asyncio.run(main())
