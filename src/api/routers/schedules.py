"""API routes for Schedules — wired to Temporal Schedule API."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
)
from src.services import crud
from src.services.schedule_service import (
    validate_cron,
    create_temporal_schedule,
    update_temporal_schedule,
    delete_temporal_schedule,
    pause_temporal_schedule,
    unpause_temporal_schedule,
    describe_temporal_schedule,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    schedule_data: ScheduleCreate,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new schedule and register it with Temporal."""
    # Validate cron expression
    if not validate_cron(schedule_data.cron):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid cron expression: {schedule_data.cron}",
        )

    # Verify workflow exists and get entrypoint
    workflow = await crud.get_workflow(db=db, workflow_id=schedule_data.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create DB record first
    schedule = await crud.create_schedule(
        db=db,
        workspace_id=workspace_id,
        workflow_id=schedule_data.workflow_id,
        name=schedule_data.name,
        cron=schedule_data.cron,
        timezone=schedule_data.timezone,
        enabled=schedule_data.enabled,
    )

    # Register with Temporal
    try:
        await create_temporal_schedule(
            schedule_id=schedule.id,
            workflow_entrypoint=workflow.entrypoint_symbol,
            cron=schedule_data.cron,
            enabled=schedule_data.enabled,
        )
    except Exception as e:
        LOGGER.error("Failed to create Temporal schedule for %d: %s", schedule.id, e)
        # Clean up DB record on failure
        await crud.delete_schedule(db=db, schedule_id=schedule.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Temporal schedule: {str(e)}",
        )

    return schedule


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    workspace_id: int,
    workflow_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all schedules in a workspace."""
    schedules = await crud.list_schedules(db=db, workspace_id=workspace_id, workflow_id=workflow_id)
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a schedule by ID."""
    schedule = await crud.get_schedule(db=db, schedule_id=schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/{schedule_id}/temporal-info")
async def get_schedule_temporal_info(schedule_id: int):
    """Get Temporal-side information for a schedule (recent actions, next run times)."""
    info = await describe_temporal_schedule(schedule_id)
    if info is None:
        raise HTTPException(
            status_code=404,
            detail="Schedule not found in Temporal",
        )
    return info


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a schedule and sync changes to Temporal."""
    schedule = await crud.get_schedule(db=db, schedule_id=schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Validate cron if provided
    if schedule_data.cron is not None and not validate_cron(schedule_data.cron):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid cron expression: {schedule_data.cron}",
        )

    new_cron = schedule_data.cron if schedule_data.cron is not None else schedule.cron
    new_enabled = schedule_data.enabled if schedule_data.enabled is not None else schedule.enabled

    # Update DB
    schedule = await crud.update_schedule(
        db=db,
        schedule_id=schedule_id,
        cron=schedule_data.cron,
        enabled=schedule_data.enabled,
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found after update")

    # Sync to Temporal
    workflow = await crud.get_workflow(db=db, workflow_id=schedule.workflow_id)
    if workflow:
        try:
            # If only toggling enabled/disabled, use pause/unpause for efficiency
            if schedule_data.cron is None and schedule_data.enabled is not None:
                if new_enabled:
                    await unpause_temporal_schedule(schedule_id)
                else:
                    await pause_temporal_schedule(schedule_id)
            else:
                # Full update (cron changed)
                await update_temporal_schedule(
                    schedule_id=schedule_id,
                    workflow_entrypoint=workflow.entrypoint_symbol,
                    cron=new_cron,
                    enabled=new_enabled,
                )
        except Exception as e:
            LOGGER.error("Failed to update Temporal schedule %d: %s", schedule_id, e)
            # Don't roll back DB — state is eventually consistent

    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule from DB and Temporal."""
    schedule = await crud.get_schedule(db=db, schedule_id=schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Delete from Temporal first (best-effort)
    try:
        await delete_temporal_schedule(schedule_id)
    except Exception as e:
        LOGGER.warning("Failed to delete Temporal schedule %d: %s", schedule_id, e)

    # Delete from DB
    await crud.delete_schedule(db=db, schedule_id=schedule_id)
