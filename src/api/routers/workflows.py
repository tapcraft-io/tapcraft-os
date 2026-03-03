"""API routes for Workflows."""

import json
import logging
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
from src.services.code_generator import CodeGeneratorService
from src.services.git_service import GitService

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])

_code_generator = CodeGeneratorService()
_git_service = GitService()


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


@router.get("/{workflow_id}/code")
async def get_workflow_code(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the generated code for a workflow."""
    workflow = await crud.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    parts = workflow.code_module_path.split(".")
    workspace_id = int(parts[1].replace("workspace_", ""))
    slug = parts[-1]

    code = _git_service.read_workflow_code(
        workspace_id=workspace_id, workflow_slug=slug
    )

    if not code:
        raise HTTPException(status_code=404, detail="Workflow code not found on disk")

    return {"code": code, "module_path": workflow.code_module_path}


@router.post("/{workflow_id}/regenerate")
async def regenerate_workflow_code(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate Temporal workflow code from the current graph state.

    Called after manual graph edits (add/remove nodes, change config, add/remove edges)
    to keep the generated Python code in sync with the graph.
    """
    # 1. Load workflow
    workflow = await crud.get_workflow(db=db, workflow_id=workflow_id, load_graph=True)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    graph = workflow.graph
    if not graph:
        raise HTTPException(status_code=404, detail="Workflow has no graph")

    # 2. Build activity_operations map for any activity_operation nodes
    activity_operations_map = {}
    op_ids = [n.activity_operation_id for n in graph.nodes if n.activity_operation_id]
    if op_ids:
        activities = await crud.list_activities(db=db, workspace_id=workflow.workspace_id)
        for act in activities:
            for op in act.operations:
                if op.id in op_ids:
                    activity_operations_map[op.id] = {
                        "code_symbol": op.code_symbol,
                        "name": op.name,
                        "display_name": op.display_name,
                        "activity_name": act.name,
                        "config_schema": op.config_schema,
                    }

    # 3. Build graph_data dict for code generator
    graph_data = {
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "label": n.label,
                "config": n.config,
                "activity_operation_id": n.activity_operation_id,
                "primitive_type": n.primitive_type,
            }
            for n in graph.nodes
        ],
        "edges": [
            {
                "from_node_id": e.from_node_id,
                "to_node_id": e.to_node_id,
                "path": e.path,
            }
            for e in graph.edges
        ],
        "entry_node_id": graph.entry_node_id,
    }

    # 4. Derive class name from workflow name
    workflow_class_name = "".join(
        word.capitalize() for word in workflow.name.split()
    )

    # 5. Generate code
    workflow_code = _code_generator.generate_workflow_from_graph(
        workflow_name=workflow_class_name,
        graph_data=graph_data,
        activity_operations=activity_operations_map,
    )

    # 6. Write to disk
    # Extract workspace_id and slug from code_module_path
    # Format: workspace.workspace_{id}.workflows.{slug}
    parts = workflow.code_module_path.split(".")
    ws_id = int(parts[1].replace("workspace_", ""))
    slug = parts[-1]

    code_module_path = _git_service.write_workflow_code(
        workspace_id=ws_id,
        workflow_slug=slug,
        code=workflow_code,
    )

    LOGGER.info(
        f"Regenerated code for workflow {workflow_id} ({workflow.name}): "
        f"{len(graph.nodes)} nodes, {len(graph.edges)} edges"
    )

    return {"code": workflow_code, "module_path": code_module_path}
