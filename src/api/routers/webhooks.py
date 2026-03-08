"""API routes for webhook management and inbound webhook triggers."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import WebhookCreate, WebhookResponse, WebhookUpdate
from src.services import crud

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    payload: WebhookCreate,
    workspace_id: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Create a new webhook trigger for a workflow."""
    # Verify workflow exists
    workflow = await crud.get_workflow(db=db, workflow_id=payload.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check path uniqueness
    existing = await crud.get_webhook_by_path(db=db, path=payload.path)
    if existing:
        raise HTTPException(status_code=409, detail="Webhook path already in use")

    webhook = await crud.create_webhook(
        db=db,
        workspace_id=workspace_id,
        workflow_id=payload.workflow_id,
        path=payload.path,
        secret=payload.secret,
        enabled=payload.enabled,
    )
    return webhook


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    workspace_id: int = 1,
    workflow_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all webhooks in a workspace."""
    return await crud.list_webhooks(db=db, workspace_id=workspace_id, workflow_id=workflow_id)


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a webhook by ID."""
    webhook = await crud.get_webhook(db=db, webhook_id=webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a webhook."""
    # Check path uniqueness if changing
    if payload.path:
        existing = await crud.get_webhook_by_path(db=db, path=payload.path)
        if existing and existing.id != webhook_id:
            raise HTTPException(status_code=409, detail="Webhook path already in use")

    webhook = await crud.update_webhook(
        db=db,
        webhook_id=webhook_id,
        path=payload.path,
        secret=payload.secret,
        enabled=payload.enabled,
    )
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a webhook."""
    deleted = await crud.delete_webhook(db=db, webhook_id=webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"deleted": True}
