"""API routes for Schedules."""

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

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    schedule_data: ScheduleCreate,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new schedule."""
    schedule = await crud.create_schedule(
        db=db,
        workspace_id=workspace_id,
        workflow_id=schedule_data.workflow_id,
        name=schedule_data.name,
        cron=schedule_data.cron,
        timezone=schedule_data.timezone,
        enabled=schedule_data.enabled,
    )
    return schedule


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    workspace_id: int,
    workflow_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all schedules in a workspace."""
    schedules = await crud.list_schedules(
        db=db, workspace_id=workspace_id, workflow_id=workflow_id
    )
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


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a schedule."""
    schedule = await crud.update_schedule(
        db=db,
        schedule_id=schedule_id,
        cron=schedule_data.cron,
        enabled=schedule_data.enabled,
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule."""
    success = await crud.delete_schedule(db=db, schedule_id=schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
