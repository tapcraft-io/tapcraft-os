"""API routes for agent-based workflow creation."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.db.base import get_db
from src.services.workflow_orchestrator import WorkflowOrchestrator
from src.models.schemas import WorkflowResponse, GraphResponse, AgentSessionResponse

router = APIRouter(prefix="/agent/workflows", tags=["agent", "workflows"])

orchestrator = WorkflowOrchestrator()


class CreateWorkflowRequest(BaseModel):
    """Request to create a workflow via agent."""

    user_prompt: str
    available_apps: Optional[List[int]] = None


class CreateWorkflowResponse(BaseModel):
    """Response from workflow creation."""

    workflow: WorkflowResponse
    graph: GraphResponse
    code_preview: str
    agent_session_id: int


@router.post("", response_model=CreateWorkflowResponse, status_code=201)
async def create_workflow_from_prompt(
    request: CreateWorkflowRequest,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a complete workflow from a natural language prompt.

    The agent will:
    1. Parse the prompt
    2. Generate a graph structure (nodes + edges)
    3. Generate Temporal workflow code
    4. Write code to disk
    5. Create workflow and graph records in database
    6. Return the complete workflow ready for execution
    """

    try:
        result = await orchestrator.create_workflow_from_prompt(
            db=db,
            workspace_id=workspace_id,
            user_prompt=request.user_prompt,
            available_apps=request.available_apps,
        )

        workflow = result["workflow"]
        graph = result["graph"]
        code = result["code"]
        agent_session_id = result["agent_session_id"]

        # Reload workflow with graph
        from src.services import crud

        workflow = await crud.get_workflow(
            db=db, workflow_id=workflow.id, load_graph=True
        )

        # Convert to response models
        from src.models.schemas import WorkflowResponse, GraphResponse

        workflow_response = WorkflowResponse.model_validate(workflow)
        graph_response = GraphResponse.model_validate(graph)

        # Truncate code for preview
        code_preview = code[:500] + "..." if len(code) > 500 else code

        return CreateWorkflowResponse(
            workflow=workflow_response,
            graph=graph_response,
            code_preview=code_preview,
            agent_session_id=agent_session_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@router.get("/{workflow_id}/code")
async def get_workflow_code(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the generated code for a workflow."""
    from src.services import crud

    workflow = await crud.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Extract workspace_id and slug from code_module_path
    # Format: workspace.workspace_{id}.workflows.{slug}
    parts = workflow.code_module_path.split(".")
    workspace_id = int(parts[1].replace("workspace_", ""))
    slug = parts[-1]

    code = orchestrator.git_service.read_workflow_code(
        workspace_id=workspace_id, workflow_slug=slug
    )

    if not code:
        raise HTTPException(status_code=404, detail="Workflow code not found on disk")

    return {"code": code, "module_path": workflow.code_module_path}
