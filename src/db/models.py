"""SQLAlchemy models for Tapcraft domain entities."""

from datetime import datetime
from typing import Optional
import json

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
    """User or team workspace containing all apps and workflows."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    apps: Mapped[list["App"]] = relationship(
        "App", back_populates="workspace", cascade="all, delete-orphan"
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
    agent_sessions: Mapped[list["AgentSession"]] = relationship(
        "AgentSession", back_populates="workspace", cascade="all, delete-orphan"
    )


class App(Base):
    """Reusable, code-backed capability that can be invoked as a node in workflows."""

    __tablename__ = "apps"

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
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="apps")
    operations: Mapped[list["AppOperation"]] = relationship(
        "AppOperation", back_populates="app", cascade="all, delete-orphan"
    )
    graph: Mapped[Optional["Graph"]] = relationship(
        "Graph", foreign_keys=[graph_id], post_update=True
    )


class AppOperation(Base):
    """Callable operation exposed by an App (used as a node type)."""

    __tablename__ = "app_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("apps.id"), nullable=False)
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
    app: Mapped["App"] = relationship("App", back_populates="operations")


class Workflow(Base):
    """Temporal workflow that orchestrates Apps and primitives."""

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


class Graph(Base):
    """Visual representation of a Workflow or App's composition."""

    __tablename__ = "graphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_type: Mapped[str] = mapped_column(
        Enum("workflow", "app", name="graph_owner_type"), nullable=False
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
    """A step on the workflow/app canvas."""

    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[int] = mapped_column(ForeignKey("graphs.id"), nullable=False)
    kind: Mapped[str] = mapped_column(
        Enum("trigger", "app_operation", "primitive", "logic", name="node_kind"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    app_operation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("app_operations.id"), nullable=True
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
    app_operation: Mapped[Optional["AppOperation"]] = relationship("AppOperation")


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
        Enum("queued", "running", "succeeded", "failed", name="run_status"),
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


class AgentSession(Base):
    """Interaction with the agent to create/modify Apps or Workflows."""

    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(
        Enum("app", "workflow", name="agent_target_type"), nullable=False
    )
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mode: Mapped[str] = mapped_column(
        Enum("create", "modify", "debug", name="agent_mode"), nullable=False
    )
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graph_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code_diff_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("draft", "applied", "rejected", name="agent_session_status"),
        nullable=False,
        default="draft",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="agent_sessions")
