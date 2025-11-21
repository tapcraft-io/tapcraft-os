"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Workspace Schemas
# ============================================================================


class WorkspaceCreate(BaseModel):
    """Schema for creating a workspace."""

    owner_id: str
    name: str


class WorkspaceResponse(BaseModel):
    """Schema for workspace response."""

    id: int
    owner_id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# App Schemas
# ============================================================================


class AppCreate(BaseModel):
    """Schema for creating an app."""

    name: str
    slug: str
    code_module_path: str
    description: Optional[str] = None
    category: Optional[str] = None


class AppUpdate(BaseModel):
    """Schema for updating an app."""

    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class AppOperationResponse(BaseModel):
    """Schema for app operation response."""

    id: int
    app_id: int
    name: str
    display_name: str
    description: Optional[str]
    config_schema: str
    code_symbol: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppResponse(BaseModel):
    """Schema for app response."""

    id: int
    workspace_id: int
    name: str
    slug: str
    description: Optional[str]
    category: Optional[str]
    code_module_path: str
    graph_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    operations: List[AppOperationResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# AppOperation Schemas
# ============================================================================


class AppOperationCreate(BaseModel):
    """Schema for creating an app operation."""

    name: str
    display_name: str
    code_symbol: str
    config_schema: str = "{}"
    description: Optional[str] = None


# ============================================================================
# Workflow Schemas
# ============================================================================


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""

    name: str
    slug: str
    code_module_path: str
    entrypoint_symbol: str
    description: Optional[str] = None


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""

    name: Optional[str] = None
    description: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""

    id: int
    workspace_id: int
    name: str
    slug: str
    description: Optional[str]
    graph_id: int
    code_module_path: str
    entrypoint_symbol: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Graph Schemas
# ============================================================================


class NodeResponse(BaseModel):
    """Schema for node response."""

    id: int
    graph_id: int
    kind: str
    label: str
    app_operation_id: Optional[int]
    primitive_type: Optional[str]
    config: str
    config_schema: str
    ui_position: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EdgeResponse(BaseModel):
    """Schema for edge response."""

    id: int
    graph_id: int
    from_node_id: int
    to_node_id: int
    path: Optional[str]
    label: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GraphResponse(BaseModel):
    """Schema for graph response."""

    id: int
    workspace_id: int
    owner_type: str
    owner_id: int
    entry_node_id: Optional[int]
    layout_metadata: str
    version: int
    nodes: List[NodeResponse] = []
    edges: List[EdgeResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NodeCreate(BaseModel):
    """Schema for creating a node."""

    kind: str
    label: str
    config: str = "{}"
    config_schema: str = "{}"
    ui_position: str = '{"x": 0, "y": 0}'
    app_operation_id: Optional[int] = None
    primitive_type: Optional[str] = None


class NodeUpdate(BaseModel):
    """Schema for updating a node."""

    label: Optional[str] = None
    config: Optional[str] = None
    ui_position: Optional[str] = None


class EdgeCreate(BaseModel):
    """Schema for creating an edge."""

    from_node_id: int
    to_node_id: int
    path: Optional[str] = None
    label: Optional[str] = None


class GraphUpdate(BaseModel):
    """Schema for updating a graph."""

    entry_node_id: Optional[int] = None
    layout_metadata: Optional[str] = None


# ============================================================================
# Schedule Schemas
# ============================================================================


class ScheduleCreate(BaseModel):
    """Schema for creating a schedule."""

    workflow_id: int
    name: str
    cron: str
    timezone: str = "UTC"
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule."""

    cron: Optional[str] = None
    enabled: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Schema for schedule response."""

    id: int
    workspace_id: int
    workflow_id: int
    name: str
    cron: str
    timezone: str
    enabled: bool
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Run Schemas
# ============================================================================


class RunCreate(BaseModel):
    """Schema for creating a run."""

    workflow_id: int
    input_config: str = "{}"


class RunUpdate(BaseModel):
    """Schema for updating a run."""

    status: Optional[str] = None
    summary: Optional[str] = None
    error_excerpt: Optional[str] = None


class RunResponse(BaseModel):
    """Schema for run response."""

    id: int
    workspace_id: int
    workflow_id: int
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    summary: Optional[str]
    error_excerpt: Optional[str]
    input_config: str
    temporal_workflow_id: Optional[str]
    temporal_run_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# AgentSession Schemas
# ============================================================================


class AgentSessionCreate(BaseModel):
    """Schema for creating an agent session."""

    target_type: str  # "app" or "workflow"
    mode: str  # "create", "modify", "debug"
    user_prompt: str
    target_id: Optional[int] = None


class AgentSessionUpdate(BaseModel):
    """Schema for updating an agent session."""

    plan: Optional[str] = None
    graph_diff: Optional[str] = None
    code_diff_summary: Optional[str] = None
    status: Optional[str] = None
    target_id: Optional[int] = None


class AgentSessionResponse(BaseModel):
    """Schema for agent session response."""

    id: int
    workspace_id: int
    target_type: str
    target_id: Optional[int]
    mode: str
    user_prompt: str
    plan: Optional[str]
    graph_diff: Optional[str]
    code_diff_summary: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
