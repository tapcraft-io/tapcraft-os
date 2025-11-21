"""API routes for Runs."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    RunCreate,
    RunUpdate,
    RunResponse,
)
from src.services import crud

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    run_data: RunCreate,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new run."""
    run = await crud.create_run(
        db=db,
        workspace_id=workspace_id,
        workflow_id=run_data.workflow_id,
        input_config=run_data.input_config,
    )
    return run


@router.get("", response_model=List[RunResponse])
async def list_runs(
    workspace_id: int,
    workflow_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all runs in a workspace."""
    runs = await crud.list_runs(
        db=db, workspace_id=workspace_id, workflow_id=workflow_id, status=status
    )
    return runs


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a run by ID."""
    run = await crud.get_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.patch("/{run_id}", response_model=RunResponse)
async def update_run(
    run_id: int,
    run_data: RunUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a run."""
    run = await crud.update_run(
        db=db,
        run_id=run_id,
        status=run_data.status,
        summary=run_data.summary,
        error_excerpt=run_data.error_excerpt,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
