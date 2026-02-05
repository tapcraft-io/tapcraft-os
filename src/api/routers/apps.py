"""API routes for Apps."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    AppCreate,
    AppUpdate,
    AppResponse,
    AppOperationCreate,
    AppOperationResponse,
)
from src.services import crud

router = APIRouter(prefix="/apps", tags=["apps"])


@router.post("", response_model=AppResponse, status_code=201)
async def create_app(
    app_data: AppCreate,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new app."""
    app = await crud.create_app(
        db=db,
        workspace_id=workspace_id,
        name=app_data.name,
        slug=app_data.slug,
        code_module_path=app_data.code_module_path,
        description=app_data.description,
        category=app_data.category,
    )
    return app


@router.get("", response_model=List[AppResponse])
async def list_apps(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all apps in a workspace."""
    apps = await crud.list_apps(db=db, workspace_id=workspace_id)
    return apps


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get an app by ID."""
    app = await crud.get_app(db=db, app_id=app_id, load_operations=True)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.patch("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: int,
    app_data: AppUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an app."""
    app = await crud.update_app(
        db=db,
        app_id=app_id,
        name=app_data.name,
        description=app_data.description,
        category=app_data.category,
    )
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.delete("/{app_id}", status_code=204)
async def delete_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an app."""
    success = await crud.delete_app(db=db, app_id=app_id)
    if not success:
        raise HTTPException(status_code=404, detail="App not found")


@router.post("/{app_id}/operations", response_model=AppOperationResponse, status_code=201)
async def create_app_operation(
    app_id: int,
    operation_data: AppOperationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new app operation."""
    operation = await crud.create_app_operation(
        db=db,
        app_id=app_id,
        name=operation_data.name,
        display_name=operation_data.display_name,
        code_symbol=operation_data.code_symbol,
        config_schema=operation_data.config_schema,
        description=operation_data.description,
    )
    return operation


@router.get("/{app_id}/operations", response_model=List[AppOperationResponse])
async def list_app_operations(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all operations for an app."""
    operations = await crud.list_app_operations(db=db, app_id=app_id)
    return operations
