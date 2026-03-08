"""SQLAlchemy models for Tapcraft domain entities."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Workspace(Base):
    """User or team workspace containing all activities and workflows."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repo_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="main")
    repo_auth_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sync_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="workspace", cascade="all, delete-orphan"
    )
    workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow", back_populates="workspace", cascade="all, delete-orphan"
    )
    graphs: Mapped[list["Graph"]] = relationship(
        "Graph", back_populates="workspace", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule", back_populates="workspace", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="workspace", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["Webhook"]] = relationship(
        "Webhook", back_populates="workspace", cascade="all, delete-orphan"
    )
    oauth_providers: Mapped[list["OAuthProvider"]] = relationship(
        "OAuthProvider", back_populates="workspace", cascade="all, delete-orphan"
    )


class Activity(Base):
    """Reusable, code-backed capability that can be invoked as a node in workflows."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    code_module_path: Mapped[str] = mapped_column(String(500), nullable=False)
    graph_id: Mapped[Optional[int]] = mapped_column(ForeignKey("graphs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="activities")
    operations: Mapped[list["ActivityOperation"]] = relationship(
        "ActivityOperation", back_populates="activity", cascade="all, delete-orphan"
    )
    graph: Mapped[Optional["Graph"]] = relationship(
        "Graph", foreign_keys=[graph_id], post_update=True
    )


class ActivityOperation(Base):
    """Callable operation exposed by an Activity (used as a node type)."""

    __tablename__ = "activity_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_schema: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    code_symbol: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    activity: Mapped["Activity"] = relationship("Activity", back_populates="operations")


class Workflow(Base):
    """Temporal workflow that orchestrates Activities and primitives."""

    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graph_id: Mapped[int] = mapped_column(ForeignKey("graphs.id"), nullable=False)
    code_module_path: Mapped[str] = mapped_column(String(500), nullable=False)
    entrypoint_symbol: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="workflows")
    graph: Mapped["Graph"] = relationship(
        "Graph", foreign_keys=[graph_id], back_populates="workflow"
    )
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule", back_populates="workflow", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="workflow", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["Webhook"]] = relationship(
        "Webhook", back_populates="workflow", cascade="all, delete-orphan"
    )


class Graph(Base):
    """Visual representation of a Workflow or Activity's composition."""

    __tablename__ = "graphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_type: Mapped[str] = mapped_column(
        Enum("workflow", "activity", name="graph_owner_type"), nullable=False
    )
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_node_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    layout_metadata: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="graphs")
    nodes: Mapped[list["Node"]] = relationship(
        "Node", back_populates="graph", cascade="all, delete-orphan"
    )
    edges: Mapped[list["Edge"]] = relationship(
        "Edge", back_populates="graph", cascade="all, delete-orphan"
    )
    workflow: Mapped[Optional["Workflow"]] = relationship(
        "Workflow", foreign_keys="Workflow.graph_id", back_populates="graph"
    )


class Node(Base):
    """A step on the workflow/activity canvas."""

    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[int] = mapped_column(ForeignKey("graphs.id"), nullable=False)
    kind: Mapped[str] = mapped_column(
        Enum("trigger", "activity_operation", "primitive", "logic", name="node_kind"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_operation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("activity_operations.id"), nullable=True
    )
    primitive_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    config_schema: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    ui_position: Mapped[str] = mapped_column(
        String(100), nullable=False, default='{"x": 0, "y": 0}'
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    graph: Mapped["Graph"] = relationship("Graph", back_populates="nodes")
    activity_operation: Mapped[Optional["ActivityOperation"]] = relationship("ActivityOperation")


class Edge(Base):
    """Connection between nodes in a graph."""

    __tablename__ = "edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[int] = mapped_column(ForeignKey("graphs.id"), nullable=False)
    from_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)
    to_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)
    path: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    graph: Mapped["Graph"] = relationship("Graph", back_populates="edges")
    from_node: Mapped["Node"] = relationship("Node", foreign_keys=[from_node_id])
    to_node: Mapped["Node"] = relationship("Node", foreign_keys=[to_node_id])


class Schedule(Base):
    """Temporal schedule bound to a Workflow."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="schedules")
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="schedules")


class Run(Base):
    """Single workflow execution record."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("queued", "running", "succeeded", "failed", "cancelled", name="run_status"),
        nullable=False,
        default="queued",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    temporal_workflow_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    temporal_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="runs")
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")


class Secret(Base):
    """Encrypted secret for use by activities at runtime."""

    __tablename__ = "secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Webhook(Base):
    """Inbound webhook trigger that starts a workflow execution."""

    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    trigger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="webhooks")
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="webhooks")


class OAuthProvider(Base):
    """OAuth provider configuration for external service integrations."""

    __tablename__ = "oauth_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(500), nullable=False)
    encrypted_client_secret: Mapped[str] = mapped_column(Text, nullable=False)
    auth_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    token_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    scopes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    redirect_uri: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="oauth_providers")
    credentials: Mapped[list["OAuthCredential"]] = relationship(
        "OAuthCredential", back_populates="provider", cascade="all, delete-orphan"
    )


class OAuthCredential(Base):
    """Stored OAuth tokens for an authenticated account."""

    __tablename__ = "oauth_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("oauth_providers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Bearer")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    provider: Mapped["OAuthProvider"] = relationship("OAuthProvider", back_populates="credentials")
