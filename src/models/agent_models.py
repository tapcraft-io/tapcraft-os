"""Structured models for LLM-based graph generation."""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    """Specification for a single node in the workflow graph."""

    temp_id: str = Field(
        description="Temporary ID for this node (used for edge references)"
    )
    kind: Literal["trigger", "app_operation", "primitive", "logic"] = Field(
        description="Type of node: trigger (start), app_operation (from available apps), primitive (HTTP/delay/etc), logic (conditions)"
    )
    label: str = Field(description="Human-readable label for the node")
    app_operation_id: Optional[int] = Field(
        None, description="ID of app operation (if kind=app_operation)"
    )
    primitive_type: Optional[str] = Field(
        None,
        description="Type of primitive: http_request, delay, log (if kind=primitive)",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for this node instance (e.g., HTTP URL, delay seconds)",
    )
    ui_position: Dict[str, int] = Field(
        default_factory=lambda: {"x": 0, "y": 0},
        description="Position on canvas for UI",
    )
    description: Optional[str] = Field(
        None, description="Optional description of what this node does"
    )


class EdgeSpec(BaseModel):
    """Specification for an edge connecting two nodes."""

    from_temp_id: str = Field(description="Temp ID of source node")
    to_temp_id: str = Field(description="Temp ID of target node")
    path: Optional[str] = Field(
        None, description="Path type: success, error, or custom condition"
    )
    label: Optional[str] = Field(None, description="Optional label for the edge")


class GraphSpec(BaseModel):
    """Complete graph specification for a workflow."""

    name: str = Field(description="Name of the workflow (e.g., 'Daily Email Digest')")
    description: str = Field(
        description="Detailed description of what this workflow does"
    )
    nodes: List[NodeSpec] = Field(
        description="All nodes in the workflow graph, in topological order if possible"
    )
    edges: List[EdgeSpec] = Field(
        description="All edges connecting nodes in the workflow"
    )
    entry_node_temp_id: str = Field(
        description="Temp ID of the entry/trigger node where workflow starts"
    )
    reasoning: Optional[str] = Field(
        None, description="LLM's reasoning about the workflow design"
    )
    estimated_complexity: Optional[str] = Field(
        None, description="Estimated complexity: simple, medium, complex"
    )


class WorkflowGenerationRequest(BaseModel):
    """Request to generate a workflow via LLM."""

    user_prompt: str = Field(
        description="Natural language description of desired workflow"
    )
    available_apps: List[Dict[str, Any]] = Field(
        description="Available apps with their operations"
    )
    constraints: List[str] = Field(
        default_factory=list, description="Additional constraints or requirements"
    )
    style_preference: Optional[str] = Field(
        None, description="Style preference: minimal, detailed, defensive (with retries)"
    )


class AppInfo(BaseModel):
    """Information about an available app for the LLM."""

    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    operations: List["OperationInfo"]


class OperationInfo(BaseModel):
    """Information about an app operation."""

    id: int
    name: str
    display_name: str
    description: Optional[str]
    config_schema: Dict[str, Any]
    example_config: Optional[Dict[str, Any]] = None


class PrimitiveInfo(BaseModel):
    """Information about built-in primitives."""

    type: str
    name: str
    description: str
    config_schema: Dict[str, Any]
    example_config: Optional[Dict[str, Any]] = None


# Built-in primitives that are always available
BUILT_IN_PRIMITIVES = [
    PrimitiveInfo(
        type="http_request",
        name="HTTP Request",
        description="Make an HTTP request to any URL (GET, POST, PUT, DELETE, etc.)",
        config_schema={
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                "url": {"type": "string"},
                "headers": {"type": "object"},
                "body": {"type": "string"},
            },
            "required": ["method", "url"],
        },
        example_config={
            "method": "GET",
            "url": "https://api.example.com/data",
            "headers": {"Authorization": "Bearer token"},
        },
    ),
    PrimitiveInfo(
        type="delay",
        name="Delay",
        description="Wait/sleep for a specified number of seconds",
        config_schema={
            "type": "object",
            "properties": {"seconds": {"type": "integer", "minimum": 1}},
            "required": ["seconds"],
        },
        example_config={"seconds": 60},
    ),
    PrimitiveInfo(
        type="log",
        name="Log Message",
        description="Log a message (useful for debugging or status updates)",
        config_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "level": {"type": "string", "enum": ["info", "warning", "error"]},
            },
            "required": ["message"],
        },
        example_config={"message": "Processing started", "level": "info"},
    ),
    PrimitiveInfo(
        type="browse",
        name="Browse Page",
        description="Navigate to a URL and perform browser actions (click, type, verify content, take screenshots). Uses an AI agent with Playwright for intelligent web interaction.",
        config_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
                "actions": {
                    "type": "array",
                    "description": "List of browser actions to perform",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["navigate", "click", "type", "verify", "screenshot", "evaluate"],
                            },
                            "selector": {"type": "string", "description": "CSS selector for target element"},
                            "value": {"type": "string", "description": "Value to type or verify"},
                            "name": {"type": "string", "description": "Screenshot filename"},
                            "script": {"type": "string", "description": "JavaScript to evaluate"},
                        },
                        "required": ["type"],
                    },
                },
            },
            "required": ["url", "actions"],
        },
        example_config={
            "url": "https://example.com/status",
            "actions": [
                {"type": "verify", "selector": ".status-badge", "value": "Active"},
                {"type": "screenshot", "name": "status-check.png"},
            ],
        },
    ),
]
