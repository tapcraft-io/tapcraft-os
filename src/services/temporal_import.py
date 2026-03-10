"""Service for importing workflows and schedules from an existing Temporal namespace.

Connects to a Temporal cluster, discovers running workflow types and registered
schedules, and creates corresponding Workflow, Graph, Schedule, and Run records
in the Tapcraft database.  The import is idempotent — re-running it will skip
any items that have already been imported.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from temporalio.api.enums.v1 import WorkflowExecutionStatus
from temporalio.client import Client

from src.services import crud

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    """Convert a workflow type name into a URL-safe slug.

    Example: ``SignalPipelineWorkflow`` -> ``signal-pipeline-workflow``
    """
    # Insert hyphens before uppercase letters (CamelCase -> kebab-case)
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", name)
    s = s.lower().strip()
    s = _NON_ALNUM.sub("-", s)
    return s.strip("-")


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
# Discovery
# ---------------------------------------------------------------------------


async def discover_workflow_types(client: Client) -> List[Dict[str, Any]]:
    """Discover unique workflow types from running and recently completed executions.

    Returns a list of dicts, each containing:
        - ``workflow_type``: The Temporal workflow type name (class name).
        - ``task_queue``: The task queue observed on the most recent execution.
        - ``sample_workflow_id``: An example workflow ID for reference.
    """
    seen: Dict[str, Dict[str, Any]] = {}

    queries = [
        "ExecutionStatus = 'Running'",
        "ExecutionStatus = 'Completed'",
    ]

    for query in queries:
        try:
            async for wf in client.list_workflows(query=query):
                wf_type = wf.workflow_type
                if wf_type and wf_type not in seen:
                    seen[wf_type] = {
                        "workflow_type": wf_type,
                        "task_queue": getattr(wf, "task_queue", None) or "default",
                        "sample_workflow_id": wf.id,
                    }
        except Exception as exc:
            LOGGER.warning("Failed to list workflows with query '%s': %s", query, exc)

    result = sorted(seen.values(), key=lambda d: d["workflow_type"])
    LOGGER.info("Discovered %d unique workflow types from Temporal", len(result))
    return result


async def discover_schedules(client: Client) -> List[Dict[str, Any]]:
    """Discover all schedules registered in the Temporal namespace.

    Returns a list of dicts, each containing:
        - ``schedule_id``: The Temporal schedule ID.
        - ``workflow_type``: The workflow type the schedule triggers.
        - ``cron_expressions``: List of cron expressions on the schedule.
        - ``paused``: Whether the schedule is currently paused.
        - ``last_action_time``: Datetime of the most recent action, or None.
        - ``next_action_times``: Upcoming scheduled times.
    """
    schedules: List[Dict[str, Any]] = []

    try:
        async for handle in await client.list_schedules():
            schedule_id = handle.id

            try:
                desc = await client.get_schedule_handle(schedule_id).describe()
            except Exception as exc:
                LOGGER.warning("Failed to describe schedule %s: %s", schedule_id, exc)
                continue

            sched = desc.schedule

            # Extract workflow type from the schedule action
            workflow_type: Optional[str] = None
            if sched.action and hasattr(sched.action, "workflow"):
                workflow_type = sched.action.workflow
            elif sched.action and hasattr(sched.action, "workflow_type"):
                workflow_type = sched.action.workflow_type

            # Extract cron expressions from the schedule spec
            cron_expressions: List[str] = []
            if sched.spec and sched.spec.cron_expressions:
                cron_expressions = list(sched.spec.cron_expressions)

            # Paused state
            paused = sched.state.paused if sched.state else False

            # Timing info
            info = desc.info
            last_action_time: Optional[datetime] = None
            next_action_times: List[str] = []
            if info:
                if info.recent_actions:
                    last_action = info.recent_actions[-1]
                    if last_action.scheduled_at:
                        last_action_time = last_action.scheduled_at
                if info.next_action_times:
                    next_action_times = [t.isoformat() for t in info.next_action_times]

            schedules.append(
                {
                    "schedule_id": schedule_id,
                    "workflow_type": workflow_type,
                    "cron_expressions": cron_expressions,
                    "paused": paused,
                    "last_action_time": last_action_time,
                    "next_action_times": next_action_times,
                }
            )

    except Exception as exc:
        LOGGER.error("Failed to list schedules from Temporal: %s", exc)

    LOGGER.info("Discovered %d schedules from Temporal", len(schedules))
    return schedules


# ---------------------------------------------------------------------------
# Recent execution backfill
# ---------------------------------------------------------------------------


async def _backfill_runs(
    client: Client,
    db: "AsyncSession",  # noqa: F821
    workspace_id: int,
    workflow_db_id: int,
    workflow_type: str,
    existing_temporal_ids: Set[str],
    limit: int = 50,
) -> int:
    """Backfill Run records for recent Temporal executions of a workflow type.

    Returns the number of newly created Run records.
    """
    created = 0
    count = 0

    try:
        async for wf in client.list_workflows(query=f"WorkflowType = '{workflow_type}'"):
            if count >= limit:
                break
            count += 1

            # Skip if we already track this execution
            if wf.id in existing_temporal_ids:
                continue

            status = _temporal_status_to_run_status(wf.status)

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

            run = await crud.create_run(
                db=db,
                workspace_id=workspace_id,
                workflow_id=workflow_db_id,
                input_config="{}",
                temporal_workflow_id=wf.id,
                temporal_run_id=wf.run_id if hasattr(wf, "run_id") else None,
            )

            # Set timestamps and status directly to avoid extra commits
            run.status = status
            run.started_at = start_time
            run.ended_at = close_time
            await db.commit()
            await db.refresh(run)

            created += 1

    except Exception as exc:
        LOGGER.warning(
            "Failed to backfill runs for workflow type '%s': %s",
            workflow_type,
            exc,
        )

    return created


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def import_all(
    workspace_id: int,
    client: Client,
    db: "AsyncSession",  # noqa: F821
) -> Dict[str, Any]:
    """Import all workflows and schedules from Temporal into the Tapcraft DB.

    This function is idempotent: re-running it will skip items that already
    exist (matched by slug for workflows, and by ``temporal_schedule_id`` prefix
    for schedules).

    Args:
        workspace_id: The target Tapcraft workspace to import into.
        client: A connected ``temporalio.client.Client``.
        db: An active SQLAlchemy async session.

    Returns:
        A summary dict with counts and details of imported/skipped items.
    """
    summary: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "workflows_created": 0,
        "workflows_skipped": 0,
        "schedules_created": 0,
        "schedules_skipped": 0,
        "runs_backfilled": 0,
        "errors": [],
        "workflows": [],
        "schedules": [],
    }

    # ---- 1. Discover workflow types from Temporal ---------------------------
    workflow_types = await discover_workflow_types(client)

    # Load existing workflows in this workspace for dedup
    existing_workflows = await crud.list_workflows(db=db, workspace_id=workspace_id)
    existing_slugs: Dict[str, Any] = {w.slug: w for w in existing_workflows}

    # Build a mapping from workflow_type -> DB workflow for schedule linking
    type_to_db_workflow: Dict[str, Any] = {}

    for wf_info in workflow_types:
        wf_type = wf_info["workflow_type"]
        slug = _slugify(wf_type)

        if slug in existing_slugs:
            # Already imported — record for schedule linking and skip
            type_to_db_workflow[wf_type] = existing_slugs[slug]
            summary["workflows_skipped"] += 1
            summary["workflows"].append(
                {
                    "workflow_type": wf_type,
                    "slug": slug,
                    "status": "skipped",
                    "reason": "already exists",
                }
            )
            continue

        try:
            # Create an empty Graph first (required by the Workflow model)
            graph = await crud.create_graph(
                db=db,
                workspace_id=workspace_id,
                owner_type="workflow",
                owner_id=0,  # Placeholder — updated after workflow creation
                layout_metadata='{"imported_from": "temporal"}',
            )

            # Human-friendly name from CamelCase
            display_name = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", wf_type)

            workflow = await crud.create_workflow(
                db=db,
                workspace_id=workspace_id,
                name=display_name,
                slug=slug,
                graph_id=graph.id,
                code_module_path=f"imported.{slug}",
                entrypoint_symbol=wf_type,
                description=f"Imported from Temporal. Type: {wf_type}",
            )

            # Update the graph to point back to the workflow
            graph.owner_id = workflow.id
            await db.commit()
            await db.refresh(graph)

            type_to_db_workflow[wf_type] = workflow
            existing_slugs[slug] = workflow

            summary["workflows_created"] += 1
            summary["workflows"].append(
                {
                    "workflow_type": wf_type,
                    "slug": slug,
                    "workflow_id": workflow.id,
                    "graph_id": graph.id,
                    "status": "created",
                }
            )

            LOGGER.info(
                "Imported workflow type '%s' as workflow id=%d slug=%s",
                wf_type,
                workflow.id,
                slug,
            )

        except Exception as exc:
            msg = f"Failed to import workflow type '{wf_type}': {exc}"
            LOGGER.error(msg)
            summary["errors"].append(msg)

    # ---- 2. Discover and import schedules -----------------------------------
    temporal_schedules = await discover_schedules(client)

    # Load existing schedules for dedup (match by name containing the Temporal ID)
    existing_schedules = await crud.list_schedules(db=db, workspace_id=workspace_id)
    existing_schedule_names: Set[str] = {s.name for s in existing_schedules}

    for sched_info in temporal_schedules:
        temporal_sched_id = sched_info["schedule_id"]
        wf_type = sched_info.get("workflow_type")
        cron_list = sched_info.get("cron_expressions", [])
        paused = sched_info.get("paused", False)

        # Build a deterministic name for dedup
        schedule_name = f"imported:{temporal_sched_id}"

        if schedule_name in existing_schedule_names:
            summary["schedules_skipped"] += 1
            summary["schedules"].append(
                {
                    "temporal_schedule_id": temporal_sched_id,
                    "status": "skipped",
                    "reason": "already exists",
                }
            )
            continue

        # Link to the DB workflow by type
        db_workflow = type_to_db_workflow.get(wf_type) if wf_type else None
        if not db_workflow:
            msg = (
                f"Schedule '{temporal_sched_id}' references workflow type "
                f"'{wf_type}' which was not imported — skipping"
            )
            LOGGER.warning(msg)
            summary["errors"].append(msg)
            summary["schedules"].append(
                {
                    "temporal_schedule_id": temporal_sched_id,
                    "workflow_type": wf_type,
                    "status": "skipped",
                    "reason": "no matching workflow",
                }
            )
            continue

        cron_expr = cron_list[0] if cron_list else "0 * * * *"

        try:
            schedule = await crud.create_schedule(
                db=db,
                workspace_id=workspace_id,
                workflow_id=db_workflow.id,
                name=schedule_name,
                cron=cron_expr,
                timezone="UTC",
                enabled=not paused,
            )

            # Sync timing from Temporal
            last_action = sched_info.get("last_action_time")
            if last_action and isinstance(last_action, datetime):
                schedule.last_run_at = last_action

            next_times = sched_info.get("next_action_times", [])
            if next_times:
                try:
                    schedule.next_run_at = datetime.fromisoformat(next_times[0])
                except (ValueError, TypeError):
                    pass

            await db.commit()
            await db.refresh(schedule)

            summary["schedules_created"] += 1
            summary["schedules"].append(
                {
                    "temporal_schedule_id": temporal_sched_id,
                    "schedule_id": schedule.id,
                    "workflow_type": wf_type,
                    "cron": cron_expr,
                    "enabled": not paused,
                    "status": "created",
                }
            )

            LOGGER.info(
                "Imported schedule '%s' (cron=%s, enabled=%s) -> schedule id=%d",
                temporal_sched_id,
                cron_expr,
                not paused,
                schedule.id,
            )

        except Exception as exc:
            msg = f"Failed to import schedule '{temporal_sched_id}': {exc}"
            LOGGER.error(msg)
            summary["errors"].append(msg)

    # ---- 3. Backfill recent Run records ------------------------------------
    # Collect existing temporal_workflow_ids to avoid duplicate backfill
    existing_runs = await crud.list_runs(db=db, workspace_id=workspace_id)
    existing_temporal_ids: Set[str] = {
        r.temporal_workflow_id for r in existing_runs if r.temporal_workflow_id
    }

    for wf_type, db_workflow in type_to_db_workflow.items():
        backfilled = await _backfill_runs(
            client=client,
            db=db,
            workspace_id=workspace_id,
            workflow_db_id=db_workflow.id,
            workflow_type=wf_type,
            existing_temporal_ids=existing_temporal_ids,
        )
        summary["runs_backfilled"] += backfilled

    LOGGER.info(
        "Import complete: %d workflows created, %d skipped, "
        "%d schedules created, %d skipped, %d runs backfilled",
        summary["workflows_created"],
        summary["workflows_skipped"],
        summary["schedules_created"],
        summary["schedules_skipped"],
        summary["runs_backfilled"],
    )

    return summary
