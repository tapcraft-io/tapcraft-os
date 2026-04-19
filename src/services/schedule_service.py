"""Service for managing Temporal schedules."""

from __future__ import annotations

import inspect
import logging
import os
import re
from typing import Any

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
    ScheduleUpdateInput,
)

from src.config.defaults import WORKFLOW_EXECUTION_TIMEOUT, WORKFLOW_RUN_TIMEOUT

LOGGER = logging.getLogger(__name__)

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TASK_QUEUE = os.getenv("TASK_QUEUE", "default")


from src.services.workflow_resolver import resolve_workflow_class as _resolve_workflow_class

# Standard 5-field cron regex (minute hour dom month dow), allowing special chars
_CRON_RE = re.compile(
    r"^(@(annually|yearly|monthly|weekly|daily|hourly|reboot)"
    r"|(((\d+|\*)(\/\d+)?(,(\d+|\*)(\/\d+)?)*)\s+){4}"
    r"((\d+|\*)(\/\d+)?(,(\d+|\*)(\/\d+)?)*))$"
)


def validate_cron(expression: str) -> bool:
    """Validate a cron expression (5-field standard or @shorthand).

    Returns True if the expression looks valid.
    """
    expr = expression.strip()
    # Allow common shorthands
    if expr.startswith("@"):
        return expr in (
            "@annually",
            "@yearly",
            "@monthly",
            "@weekly",
            "@daily",
            "@hourly",
            "@reboot",
        )
    parts = expr.split()
    if len(parts) != 5:
        return False
    # Per-field quick check: each field must contain digits, *, /, -, or ,
    field_re = re.compile(r"^[\d\*\/\-\,\?LW#]+$")
    return all(field_re.match(p) for p in parts)


def _schedule_id(db_schedule_id: int) -> str:
    """Deterministic Temporal schedule ID from our DB schedule ID."""
    return f"tapcraft-schedule-{db_schedule_id}"


async def _get_client() -> Client:
    return await Client.connect(TEMPORAL_ADDRESS)


def _workflow_takes_args(workflow_class: Any) -> bool:
    """Return True if the workflow's run() method accepts parameters beyond self."""
    try:
        sig = inspect.signature(workflow_class.run)
    except (ValueError, TypeError):
        return True
    return any(p.name != "self" for p in sig.parameters.values())


def _build_schedule_action(
    workflow_class: Any,
    temporal_id: str,
    input_config: dict | None,
) -> ScheduleActionStartWorkflow:
    """Build a ScheduleActionStartWorkflow, omitting args when the workflow takes none.

    Temporal's ScheduleActionStartWorkflow forwards positional args to the workflow's
    run() method. Passing an input dict to a workflow that declares ``run(self)``
    raises ``TypeError: run() takes 1 positional argument but 2 were given`` at
    activation time. Inspect the signature so no-arg workflows get no args.
    """
    kwargs: dict[str, Any] = dict(
        id=f"scheduled-{temporal_id}-{{{{.ScheduledTime}}}}",
        task_queue=TASK_QUEUE,
        execution_timeout=WORKFLOW_EXECUTION_TIMEOUT,
        run_timeout=WORKFLOW_RUN_TIMEOUT,
    )
    if _workflow_takes_args(workflow_class):
        return ScheduleActionStartWorkflow(
            workflow_class.run, input_config or {}, **kwargs
        )
    return ScheduleActionStartWorkflow(workflow_class.run, **kwargs)


async def create_temporal_schedule(
    schedule_id: int,
    workflow_entrypoint: str,
    cron: str,
    enabled: bool = True,
    input_config: dict | None = None,
) -> str:
    """Create a Temporal schedule for a workflow.

    Args:
        schedule_id: DB schedule primary key.
        workflow_entrypoint: e.g. "workspace.workspace_1.workflows.my_wf.MyWorkflow"
        cron: 5-field cron expression.
        enabled: whether the schedule fires immediately.
        input_config: optional dict passed as workflow arg.

    Returns:
        The Temporal schedule ID.
    """
    client = await _get_client()

    workflow_class = _resolve_workflow_class(workflow_entrypoint)

    temporal_id = _schedule_id(schedule_id)

    schedule = Schedule(
        action=_build_schedule_action(workflow_class, temporal_id, input_config),
        spec=ScheduleSpec(cron_expressions=[cron]),
        state=ScheduleState(paused=not enabled),
    )

    await client.create_schedule(temporal_id, schedule)
    LOGGER.info("Created Temporal schedule %s (enabled=%s)", temporal_id, enabled)
    return temporal_id


async def update_temporal_schedule(
    schedule_id: int,
    workflow_entrypoint: str,
    cron: str,
    enabled: bool = True,
    input_config: dict | None = None,
) -> None:
    """Update an existing Temporal schedule."""
    client = await _get_client()
    handle = client.get_schedule_handle(_schedule_id(schedule_id))

    workflow_class = _resolve_workflow_class(workflow_entrypoint)

    temporal_id = _schedule_id(schedule_id)

    def _updater(input: ScheduleUpdateInput) -> ScheduleUpdate:
        existing = input.description.schedule
        existing.action = _build_schedule_action(
            workflow_class, temporal_id, input_config
        )
        existing.spec = ScheduleSpec(cron_expressions=[cron])
        existing.state = ScheduleState(paused=not enabled)
        return ScheduleUpdate(schedule=existing)

    await handle.update(_updater)
    LOGGER.info("Updated Temporal schedule %s", temporal_id)


async def delete_temporal_schedule(schedule_id: int) -> None:
    """Delete a Temporal schedule."""
    client = await _get_client()
    handle = client.get_schedule_handle(_schedule_id(schedule_id))
    try:
        await handle.delete()
        LOGGER.info("Deleted Temporal schedule %s", _schedule_id(schedule_id))
    except Exception as e:
        if "not found" in str(e).lower():
            LOGGER.warning(
                "Schedule %s not found in Temporal (already deleted?)", _schedule_id(schedule_id)
            )
        else:
            raise


async def pause_temporal_schedule(schedule_id: int) -> None:
    """Pause a Temporal schedule."""
    client = await _get_client()
    handle = client.get_schedule_handle(_schedule_id(schedule_id))
    await handle.pause(note="Paused via Tapcraft API")
    LOGGER.info("Paused Temporal schedule %s", _schedule_id(schedule_id))


async def unpause_temporal_schedule(schedule_id: int) -> None:
    """Unpause (resume) a Temporal schedule."""
    client = await _get_client()
    handle = client.get_schedule_handle(_schedule_id(schedule_id))
    await handle.unpause(note="Resumed via Tapcraft API")
    LOGGER.info("Unpaused Temporal schedule %s", _schedule_id(schedule_id))


async def describe_temporal_schedule(schedule_id: int) -> dict | None:
    """Describe a Temporal schedule, returning info or None if not found."""
    client = await _get_client()
    handle = client.get_schedule_handle(_schedule_id(schedule_id))
    try:
        desc = await handle.describe()
        info = desc.info
        return {
            "temporal_id": _schedule_id(schedule_id),
            "paused": desc.schedule.state.paused if desc.schedule.state else False,
            "num_actions_taken": info.num_actions if info else 0,
            "recent_actions": [
                {
                    "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                }
                for a in (info.recent_actions or [])
            ]
            if info
            else [],
            "next_action_times": [t.isoformat() for t in (info.next_action_times or [])]
            if info
            else [],
        }
    except Exception as e:
        if "not found" in str(e).lower():
            return None
        raise


async def reconcile_schedules_from_db() -> int:
    """On startup, ensure every enabled DB schedule has a Temporal schedule.

    Returns number of schedules created/reconciled.
    """
    from src.db.base import AsyncSessionLocal
    from src.services import crud
    from sqlalchemy import select
    from src.db.models import Schedule as ScheduleModel

    count = 0
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ScheduleModel).where(ScheduleModel.enabled == True)  # noqa: E712
            )
            schedules = list(result.scalars().all())

            for sched in schedules:
                # Load workflow to get entrypoint
                workflow = await crud.get_workflow(db=db, workflow_id=sched.workflow_id)
                if not workflow:
                    LOGGER.warning(
                        "Schedule %d references missing workflow %d — skipping",
                        sched.id,
                        sched.workflow_id,
                    )
                    continue

                # Reconcile: update the existing schedule (so action/cron changes
                # in code are applied on restart), or create it if missing.
                info = await describe_temporal_schedule(sched.id)
                try:
                    if info is None:
                        await create_temporal_schedule(
                            schedule_id=sched.id,
                            workflow_entrypoint=workflow.entrypoint_symbol,
                            cron=sched.cron,
                            enabled=True,
                        )
                    else:
                        await update_temporal_schedule(
                            schedule_id=sched.id,
                            workflow_entrypoint=workflow.entrypoint_symbol,
                            cron=sched.cron,
                            enabled=True,
                        )
                    count += 1
                except Exception as e:
                    LOGGER.error("Failed to reconcile schedule %d: %s", sched.id, e)

    except Exception as e:
        LOGGER.error("Failed to reconcile schedules: %s", e)

    LOGGER.info("Reconciled %d schedules with Temporal", count)
    return count
