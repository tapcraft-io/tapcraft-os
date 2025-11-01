"""Shared pydantic models for the Tapcraft OS API and services."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Capability(BaseModel):
    """Represents a callable tool surfaced to the automation agent."""

    id: str = Field(description="Unique identifier for the capability (e.g., net.http.request)")
    params_schema: Dict[str, Any] = Field(
        default_factory=dict, description="JSON schema describing input parameters"
    )
    returns_schema: Dict[str, Any] = Field(
        default_factory=dict, description="JSON schema describing return payload"
    )


class WorkflowSpec(BaseModel):
    """Metadata about a workflow that can be loaded into the worker."""

    workflow_ref: str = Field(description="Stable reference used to invoke the workflow")
    config_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional JSON schema for workflow configuration",
    )


class ScheduleSpec(BaseModel):
    """A durable schedule definition backed by Temporal."""

    name: str = Field(description="Human-friendly identifier for the schedule")
    workflow_ref: str = Field(description="Reference of the workflow to execute")
    cron: str = Field(description="Cron expression compatible with Temporal schedules")
    timezone: str = Field(description="IANA timezone identifier")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to workflow")


class RunRecord(BaseModel):
    """Minimal audit trail for workflow executions."""

    id: str
    workflow_ref: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    summary: Optional[str] = None


class AgentPrompt(BaseModel):
    """Structured request sent to the agent service."""

    task_text: str
    capabilities: List[Capability]
    constraints: List[str] = Field(default_factory=list)
    defaults: Dict[str, Any] = Field(default_factory=dict)


class AgentManifest(BaseModel):
    workflow_ref: str
    required_tools: List[str] = Field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    schedule: Optional[ScheduleSpec] = None


class AgentGeneration(BaseModel):
    """Response payload returned by the agent."""

    module_text: str
    manifest: AgentManifest


class PlanStep(BaseModel):
    """A single step inside a planning document."""

    id: str = Field(description="Stable identifier for the plan step")
    goal: str = Field(description="Outcome the step aims to achieve")
    tool_candidates: List[str] = Field(
        default_factory=list, description="Tool identifiers that could satisfy the step"
    )
    inputs_hint: Dict[str, Any] = Field(
        default_factory=dict, description="Expected inputs or configuration for the step"
    )
    outputs_hint: Dict[str, Any] = Field(
        default_factory=dict, description="Expected outputs or artifacts from the step"
    )


class PlanDoc(BaseModel):
    """Structured plan produced prior to code generation."""

    steps: List[PlanStep] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    schedule_hint: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional schedule suggestion derived from planning"
    )


class Issue(BaseModel):
    """Represents a validation issue surfaced to the user."""

    code: str = Field(description="Machine readable identifier for the issue")
    message: str = Field(description="Human readable explanation of the issue")
    location: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional location descriptor (file, line, symbol)"
    )
    fix_hint: Optional[str] = Field(
        default=None, description="Optional recommendation for resolving the issue"
    )


class ValidationDiag(BaseModel):
    """Diagnostic payload detailing validation context."""

    banned_imports: List[str] = Field(default_factory=list)
    unknown_tools: List[str] = Field(default_factory=list)
    schema_issues: List[str] = Field(default_factory=list)
    api_surface_used: List[str] = Field(default_factory=list)


class TestsSpec(BaseModel):
    """Generated unit test scaffolding for a workflow module."""

    module_path: str
    tests_text: str
    commands: List[str] = Field(default_factory=list)


class DecisionRecord(BaseModel):
    """Persisted record of an agent decision for later recall."""

    workflow_ref: str
    created_at: datetime
    model: str
    token_usage: Dict[str, int] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list)
    prompts: Dict[str, Any] = Field(default_factory=dict)
    config_keys: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class MCPServer(BaseModel):
    """Metadata about an MCP server registered with the platform."""

    name: str
    endpoint: HttpUrl
    auth: Optional[Dict[str, Any]] = Field(default=None, description="Optional auth config")


class GitChange(BaseModel):
    """Represents a file change staged for commit."""

    path: str
    content: str
    message: Optional[str] = None
