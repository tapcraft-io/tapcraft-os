"""API routes for Workflows."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
)
from src.services import crud

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    workflow_data: WorkflowCreate,
    workspace_id: int,
    graph_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow."""
    workflow = await crud.create_workflow(
        db=db,
        workspace_id=workspace_id,
        name=workflow_data.name,
        slug=workflow_data.slug,
        graph_id=graph_id,
        code_module_path=workflow_data.code_module_path,
        entrypoint_symbol=workflow_data.entrypoint_symbol,
        description=workflow_data.description,
    )
    return workflow


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all workflows in a workspace."""
    workflows = await crud.list_workflows(db=db, workspace_id=workspace_id)
    return workflows


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a workflow by ID."""
    workflow = await crud.get_workflow(db=db, workflow_id=workflow_id, load_graph=False)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    workflow_data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a workflow."""
    workflow = await crud.update_workflow(
        db=db,
        workflow_id=workflow_id,
        name=workflow_data.name,
        description=workflow_data.description,
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a workflow."""
    success = await crud.delete_workflow(db=db, workflow_id=workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
