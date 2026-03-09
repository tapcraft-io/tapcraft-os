"""API routes for importing workflows and schedules from an existing Temporal namespace.

Provides a single ``POST /import/temporal`` endpoint that connects to the
Temporal cluster configured via ``TEMPORAL_ADDRESS``, discovers running
workflow types and registered schedules, and creates corresponding records
in the Tapcraft database.

The endpoint is idempotent — running it multiple times will skip items
that have already been imported.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from src.db.base import get_db
from src.services import crud
from src.services.temporal_import import import_all

LOGGER = logging.getLogger(__name__)

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/temporal")
async def import_from_temporal(
    workspace_id: Optional[int] = Query(
        None,
        description=(
            "Target workspace ID. If omitted, the first available workspace "
            "is used. A new workspace is created if none exist."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Import workflows, schedules, and recent runs from a Temporal namespace.

    Connects to the Temporal cluster at ``TEMPORAL_ADDRESS`` and discovers:
    - Unique workflow types from running and recently completed executions.
    - All registered schedules and their cron expressions.
    - Recent execution history for each discovered workflow type.

    For each discovered item, corresponding Workflow, Graph, Schedule, and
    Run records are created in the database.  The import is idempotent —
    re-running this endpoint will skip any items that already exist.

    **Query parameters:**
    - ``workspace_id`` (optional): The workspace to import into. When
      omitted, the first available workspace is used or a new one is
      created automatically.

    **Returns:** A summary of what was imported, including counts and
    per-item details.
    """
    # Resolve or create workspace
    if workspace_id is not None:
        workspace = await crud.get_workspace(db=db, workspace_id=workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=404,
                detail=f"Workspace {workspace_id} not found",
            )
    else:
        # Use the first workspace, or create one
        workspaces = await crud.list_workspaces(db=db)
        if workspaces:
            workspace = workspaces[0]
        else:
            workspace = await crud.create_workspace(
                db=db,
                owner_id="temporal-import",
                name="Imported from Temporal",
            )
            LOGGER.info("Created workspace %d for Temporal import", workspace.id)

    # Connect to Temporal
    try:
        client = await Client.connect(TEMPORAL_ADDRESS)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to Temporal at {TEMPORAL_ADDRESS}: {exc}",
        )

    # Run the import
    try:
        summary = await import_all(
            workspace_id=workspace.id,
            client=client,
            db=db,
        )
    except Exception as exc:
        LOGGER.error("Temporal import failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {exc}",
        )

    return summary
