"""API routes for Workspaces and repo sync."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    RepoSyncResponse,
)
from src.services import crud
from src.services.repo_sync import clone_or_pull, discover_repo_activities, discover_repo_workflows

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    data: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new workspace."""
    workspace = await crud.create_workspace(
        db=db,
        owner_id=data.owner_id,
        name=data.name,
        repo_url=data.repo_url,
        repo_branch=data.repo_branch,
        repo_auth_secret=data.repo_auth_secret,
    )
    return workspace


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    owner_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List all workspaces."""
    return await crud.list_workspaces(db, owner_id=owner_id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a workspace by ID."""
    workspace = await crud.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: int,
    data: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update workspace repo configuration."""
    workspace = await crud.update_workspace(
        db=db,
        workspace_id=workspace_id,
        name=data.name,
        repo_url=data.repo_url,
        repo_branch=data.repo_branch,
        repo_auth_secret=data.repo_auth_secret,
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/{workspace_id}/sync", response_model=RepoSyncResponse)
async def sync_workspace_repo(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Clone or pull the workspace's git repo and discover activities/workflows."""
    workspace = await crud.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if not workspace.repo_url:
        raise HTTPException(status_code=400, detail="No repo_url configured for this workspace")

    sync_status, sync_error = await clone_or_pull(workspace, db)

    discovered_activities = []
    discovered_workflows = []
    if sync_status == "synced":
        discovered_activities = [
            getattr(a, "__temporal_activity_definition", {}).get("name", a.__name__)
            if hasattr(a, "__temporal_activity_definition") and isinstance(getattr(a, "__temporal_activity_definition"), dict)
            else a.__name__
            for a in discover_repo_activities(workspace_id)
        ]
        discovered_workflows = [
            cls.__name__ for cls in discover_repo_workflows(workspace_id)
        ]

    return RepoSyncResponse(
        workspace_id=workspace_id,
        sync_status=sync_status,
        sync_error=sync_error,
        last_synced_at=workspace.last_synced_at,
        discovered_activities=discovered_activities,
        discovered_workflows=discovered_workflows,
    )


@router.get("/{workspace_id}/discovered")
async def list_discovered(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List discovered activities and workflows from the workspace repo."""
    workspace = await crud.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    activities = discover_repo_activities(workspace_id)
    workflows = discover_repo_workflows(workspace_id)

    activity_names = []
    for a in activities:
        defn = getattr(a, "__temporal_activity_definition", None)
        if defn and isinstance(defn, dict):
            activity_names.append(defn.get("name", a.__name__))
        else:
            activity_names.append(a.__name__)

    workflow_names = [cls.__name__ for cls in workflows]

    return {
        "workspace_id": workspace_id,
        "activities": activity_names,
        "workflows": workflow_names,
    }
