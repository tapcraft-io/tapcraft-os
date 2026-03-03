"""API routes for Activities."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityOperationCreate,
    ActivityOperationResponse,
)
from src.services import crud

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(
    activity_data: ActivityCreate,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new activity."""
    activity = await crud.create_activity(
        db=db,
        workspace_id=workspace_id,
        name=activity_data.name,
        slug=activity_data.slug,
        code_module_path=activity_data.code_module_path,
        description=activity_data.description,
        category=activity_data.category,
    )
    return activity


@router.get("", response_model=List[ActivityResponse])
async def list_activities(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all activities in a workspace."""
    activities = await crud.list_activities(db=db, workspace_id=workspace_id)
    return activities


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get an activity by ID."""
    activity = await crud.get_activity(db=db, activity_id=activity_id, load_operations=True)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    activity_data: ActivityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an activity."""
    activity = await crud.update_activity(
        db=db,
        activity_id=activity_id,
        name=activity_data.name,
        description=activity_data.description,
        category=activity_data.category,
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an activity."""
    success = await crud.delete_activity(db=db, activity_id=activity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Activity not found")


@router.post("/{activity_id}/operations", response_model=ActivityOperationResponse, status_code=201)
async def create_activity_operation(
    activity_id: int,
    operation_data: ActivityOperationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new activity operation."""
    operation = await crud.create_activity_operation(
        db=db,
        activity_id=activity_id,
        name=operation_data.name,
        display_name=operation_data.display_name,
        code_symbol=operation_data.code_symbol,
        config_schema=operation_data.config_schema,
        description=operation_data.description,
    )
    return operation


@router.get("/{activity_id}/operations", response_model=List[ActivityOperationResponse])
async def list_activity_operations(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all operations for an activity."""
    operations = await crud.list_activity_operations(db=db, activity_id=activity_id)
    return operations


@router.get("/{activity_id}/code")
async def get_activity_code(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the source code for an activity."""
    activity = await crud.get_activity(db=db, activity_id=activity_id, load_operations=True)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    from pathlib import Path

    # code_module_path is like "workspace.workspace_1.activities.my_activity"
    parts = activity.code_module_path.split(".")
    code = None

    # Try to read from workspace disk first
    if len(parts) >= 4 and parts[0] == "workspace":
        from src.services.git_service import GitService
        git_service = GitService()
        workspace_id = int(parts[1].replace("workspace_", ""))
        workspace_path = git_service.get_workspace_path(workspace_id)
        code_file = workspace_path / ("/".join(parts[2:]) + ".py")
        if code_file.exists():
            code = code_file.read_text()

    # If no file on disk, show the registered operations as documentation
    if code is None and activity.operations:
        lines = [
            f'"""',
            f'Activity: {activity.name}',
            f'Module: {activity.code_module_path}',
            f'',
            f'{activity.description or "No description."}',
            f'',
            f'This activity is registered in the worker via ActivityRegistry.',
            f'Operations are implemented as Temporal activity stubs.',
            f'"""',
            f'',
        ]
        for op in activity.operations:
            lines.append(f'# Operation: {op.display_name}')
            lines.append(f'# Activity name: {op.code_symbol}')
            if op.description:
                lines.append(f'# {op.description}')
            if op.config_schema:
                import json
                try:
                    schema = json.loads(op.config_schema) if isinstance(op.config_schema, str) else op.config_schema
                    props = schema.get("properties", {})
                    required = schema.get("required", [])
                    if props:
                        lines.append(f'# Config schema:')
                        for k, v in props.items():
                            req = " (required)" if k in required else ""
                            lines.append(f'#   {k}: {v.get("type", "any")}{req}')
                except Exception:
                    pass
            lines.append(f'')
            lines.append(f'@activity.defn(name="{op.code_symbol}")')
            lines.append(f'async def {op.name}(config: Dict[str, Any]) -> Dict[str, Any]:')
            lines.append(f'    """{op.description or op.display_name}"""')
            lines.append(f'    ...')
            lines.append(f'')
        code = "\n".join(lines)

    return {"code": code, "module_path": activity.code_module_path}


@router.get("/{activity_id}/usage")
async def get_activity_usage(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get workflows that use this activity."""
    usage = await crud.get_activity_usage(db=db, activity_id=activity_id)
    return {"workflows": usage}
