"""CRUD operations for domain entities."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import (
    Workspace,
    App,
    AppOperation,
    Workflow,
    Graph,
    Node,
    Edge,
    Schedule,
    Run,
    AgentSession,
)


# ============================================================================
# Workspace CRUD
# ============================================================================


async def create_workspace(
    db: AsyncSession, owner_id: str, name: str
) -> Workspace:
    """Create a new workspace."""
    workspace = Workspace(owner_id=owner_id, name=name)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def get_workspace(db: AsyncSession, workspace_id: int) -> Optional[Workspace]:
    """Get a workspace by ID."""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    return result.scalars().first()


async def list_workspaces(
    db: AsyncSession, owner_id: Optional[str] = None
) -> List[Workspace]:
    """List all workspaces, optionally filtered by owner."""
    query = select(Workspace)
    if owner_id:
        query = query.where(Workspace.owner_id == owner_id)
    result = await db.execute(query)
    return list(result.scalars().all())


# ============================================================================
# App CRUD
# ============================================================================


async def create_app(
    db: AsyncSession,
    workspace_id: int,
    name: str,
    slug: str,
    code_module_path: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> App:
    """Create a new app."""
    app = App(
        workspace_id=workspace_id,
        name=name,
        slug=slug,
        code_module_path=code_module_path,
        description=description,
        category=category,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def get_app(
    db: AsyncSession, app_id: int, load_operations: bool = False
) -> Optional[App]:
    """Get an app by ID."""
    query = select(App).where(App.id == app_id)
    if load_operations:
        query = query.options(selectinload(App.operations))
    result = await db.execute(query)
    return result.scalars().first()


async def list_apps(db: AsyncSession, workspace_id: int) -> List[App]:
    """List all apps in a workspace."""
    result = await db.execute(
        select(App)
        .where(App.workspace_id == workspace_id)
        .options(selectinload(App.operations))
    )
    return list(result.scalars().all())


async def update_app(
    db: AsyncSession,
    app_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> Optional[App]:
    """Update an app."""
    app = await get_app(db, app_id)
    if not app:
        return None

    if name is not None:
        app.name = name
    if description is not None:
        app.description = description
    if category is not None:
        app.category = category

    await db.commit()
    await db.refresh(app)
    return app


async def delete_app(db: AsyncSession, app_id: int) -> bool:
    """Delete an app."""
    app = await get_app(db, app_id)
    if not app:
        return False

    await db.delete(app)
    await db.commit()
    return True


# ============================================================================
# AppOperation CRUD
# ============================================================================


async def create_app_operation(
    db: AsyncSession,
    app_id: int,
    name: str,
    display_name: str,
    code_symbol: str,
    config_schema: str = "{}",
    description: Optional[str] = None,
) -> AppOperation:
    """Create a new app operation."""
    operation = AppOperation(
        app_id=app_id,
        name=name,
        display_name=display_name,
        code_symbol=code_symbol,
        config_schema=config_schema,
        description=description,
    )
    db.add(operation)
    await db.commit()
    await db.refresh(operation)
    return operation


async def get_app_operation(
    db: AsyncSession, operation_id: int
) -> Optional[AppOperation]:
    """Get an app operation by ID."""
    result = await db.execute(
        select(AppOperation).where(AppOperation.id == operation_id)
    )
    return result.scalars().first()


async def list_app_operations(db: AsyncSession, app_id: int) -> List[AppOperation]:
    """List all operations for an app."""
    result = await db.execute(
        select(AppOperation).where(AppOperation.app_id == app_id)
    )
    return list(result.scalars().all())


# ============================================================================
# Workflow CRUD
# ============================================================================


async def create_workflow(
    db: AsyncSession,
    workspace_id: int,
    name: str,
    slug: str,
    graph_id: int,
    code_module_path: str,
    entrypoint_symbol: str,
    description: Optional[str] = None,
) -> Workflow:
    """Create a new workflow."""
    workflow = Workflow(
        workspace_id=workspace_id,
        name=name,
        slug=slug,
        graph_id=graph_id,
        code_module_path=code_module_path,
        entrypoint_symbol=entrypoint_symbol,
        description=description,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


async def get_workflow(
    db: AsyncSession, workflow_id: int, load_graph: bool = False
) -> Optional[Workflow]:
    """Get a workflow by ID."""
    query = select(Workflow).where(Workflow.id == workflow_id)
    if load_graph:
        query = query.options(
            selectinload(Workflow.graph).selectinload(Graph.nodes),
            selectinload(Workflow.graph).selectinload(Graph.edges),
        )
    result = await db.execute(query)
    return result.scalars().first()


async def list_workflows(db: AsyncSession, workspace_id: int) -> List[Workflow]:
    """List all workflows in a workspace."""
    result = await db.execute(
        select(Workflow).where(Workflow.workspace_id == workspace_id)
    )
    return list(result.scalars().all())


async def update_workflow(
    db: AsyncSession,
    workflow_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[Workflow]:
    """Update a workflow."""
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        return None

    if name is not None:
        workflow.name = name
    if description is not None:
        workflow.description = description

    await db.commit()
    await db.refresh(workflow)
    return workflow


async def delete_workflow(db: AsyncSession, workflow_id: int) -> bool:
    """Delete a workflow."""
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        return False

    await db.delete(workflow)
    await db.commit()
    return True


# ============================================================================
# Graph CRUD
# ============================================================================


async def create_graph(
    db: AsyncSession,
    workspace_id: int,
    owner_type: str,
    owner_id: int,
    entry_node_id: Optional[int] = None,
    layout_metadata: str = "{}",
) -> Graph:
    """Create a new graph."""
    graph = Graph(
        workspace_id=workspace_id,
        owner_type=owner_type,
        owner_id=owner_id,
        entry_node_id=entry_node_id,
        layout_metadata=layout_metadata,
    )
    db.add(graph)
    await db.commit()
    await db.refresh(graph)
    return graph


async def get_graph(
    db: AsyncSession, graph_id: int, load_nodes_edges: bool = True
) -> Optional[Graph]:
    """Get a graph by ID."""
    query = select(Graph).where(Graph.id == graph_id)
    if load_nodes_edges:
        query = query.options(selectinload(Graph.nodes), selectinload(Graph.edges))
    result = await db.execute(query)
    return result.scalars().first()


async def update_graph(
    db: AsyncSession,
    graph_id: int,
    entry_node_id: Optional[int] = None,
    layout_metadata: Optional[str] = None,
) -> Optional[Graph]:
    """Update a graph."""
    graph = await get_graph(db, graph_id, load_nodes_edges=False)
    if not graph:
        return None

    if entry_node_id is not None:
        graph.entry_node_id = entry_node_id
    if layout_metadata is not None:
        graph.layout_metadata = layout_metadata
    graph.version += 1

    await db.commit()
    await db.refresh(graph)
    return graph


# ============================================================================
# Node CRUD
# ============================================================================


async def create_node(
    db: AsyncSession,
    graph_id: int,
    kind: str,
    label: str,
    config: str = "{}",
    config_schema: str = "{}",
    ui_position: str = '{"x": 0, "y": 0}',
    app_operation_id: Optional[int] = None,
    primitive_type: Optional[str] = None,
) -> Node:
    """Create a new node."""
    node = Node(
        graph_id=graph_id,
        kind=kind,
        label=label,
        config=config,
        config_schema=config_schema,
        ui_position=ui_position,
        app_operation_id=app_operation_id,
        primitive_type=primitive_type,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


async def get_node(db: AsyncSession, node_id: int) -> Optional[Node]:
    """Get a node by ID."""
    result = await db.execute(select(Node).where(Node.id == node_id))
    return result.scalars().first()


async def update_node(
    db: AsyncSession,
    node_id: int,
    label: Optional[str] = None,
    config: Optional[str] = None,
    ui_position: Optional[str] = None,
) -> Optional[Node]:
    """Update a node."""
    node = await get_node(db, node_id)
    if not node:
        return None

    if label is not None:
        node.label = label
    if config is not None:
        node.config = config
    if ui_position is not None:
        node.ui_position = ui_position

    await db.commit()
    await db.refresh(node)
    return node


async def delete_node(db: AsyncSession, node_id: int) -> bool:
    """Delete a node."""
    node = await get_node(db, node_id)
    if not node:
        return False

    await db.delete(node)
    await db.commit()
    return True


# ============================================================================
# Edge CRUD
# ============================================================================


async def create_edge(
    db: AsyncSession,
    graph_id: int,
    from_node_id: int,
    to_node_id: int,
    path: Optional[str] = None,
    label: Optional[str] = None,
) -> Edge:
    """Create a new edge."""
    edge = Edge(
        graph_id=graph_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        path=path,
        label=label,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return edge


async def get_edge(db: AsyncSession, edge_id: int) -> Optional[Edge]:
    """Get an edge by ID."""
    result = await db.execute(select(Edge).where(Edge.id == edge_id))
    return result.scalars().first()


async def delete_edge(db: AsyncSession, edge_id: int) -> bool:
    """Delete an edge."""
    edge = await get_edge(db, edge_id)
    if not edge:
        return False

    await db.delete(edge)
    await db.commit()
    return True


# ============================================================================
# Schedule CRUD
# ============================================================================


async def create_schedule(
    db: AsyncSession,
    workspace_id: int,
    workflow_id: int,
    name: str,
    cron: str,
    timezone: str = "UTC",
    enabled: bool = True,
) -> Schedule:
    """Create a new schedule."""
    schedule = Schedule(
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        name=name,
        cron=cron,
        timezone=timezone,
        enabled=enabled,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_schedule(db: AsyncSession, schedule_id: int) -> Optional[Schedule]:
    """Get a schedule by ID."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    return result.scalars().first()


async def list_schedules(
    db: AsyncSession, workspace_id: int, workflow_id: Optional[int] = None
) -> List[Schedule]:
    """List all schedules, optionally filtered by workflow."""
    query = select(Schedule).where(Schedule.workspace_id == workspace_id)
    if workflow_id:
        query = query.where(Schedule.workflow_id == workflow_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_schedule(
    db: AsyncSession,
    schedule_id: int,
    cron: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Optional[Schedule]:
    """Update a schedule."""
    schedule = await get_schedule(db, schedule_id)
    if not schedule:
        return None

    if cron is not None:
        schedule.cron = cron
    if enabled is not None:
        schedule.enabled = enabled

    await db.commit()
    await db.refresh(schedule)
    return schedule


async def delete_schedule(db: AsyncSession, schedule_id: int) -> bool:
    """Delete a schedule."""
    schedule = await get_schedule(db, schedule_id)
    if not schedule:
        return False

    await db.delete(schedule)
    await db.commit()
    return True


# ============================================================================
# Run CRUD
# ============================================================================


async def create_run(
    db: AsyncSession,
    workspace_id: int,
    workflow_id: int,
    input_config: str = "{}",
    temporal_workflow_id: Optional[str] = None,
    temporal_run_id: Optional[str] = None,
) -> Run:
    """Create a new run."""
    run = Run(
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        input_config=input_config,
        temporal_workflow_id=temporal_workflow_id,
        temporal_run_id=temporal_run_id,
        status="queued",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def get_run(db: AsyncSession, run_id: int) -> Optional[Run]:
    """Get a run by ID."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    return result.scalars().first()


async def list_runs(
    db: AsyncSession,
    workspace_id: int,
    workflow_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[Run]:
    """List all runs, optionally filtered by workflow and status."""
    query = select(Run).where(Run.workspace_id == workspace_id)
    if workflow_id:
        query = query.where(Run.workflow_id == workflow_id)
    if status:
        query = query.where(Run.status == status)
    result = await db.execute(query.order_by(Run.created_at.desc()))
    return list(result.scalars().all())


async def update_run(
    db: AsyncSession,
    run_id: int,
    status: Optional[str] = None,
    summary: Optional[str] = None,
    error_excerpt: Optional[str] = None,
) -> Optional[Run]:
    """Update a run."""
    run = await get_run(db, run_id)
    if not run:
        return None

    if status is not None:
        run.status = status
        if status == "running" and not run.started_at:
            from datetime import datetime

            run.started_at = datetime.utcnow()
        elif status in ("succeeded", "failed") and not run.ended_at:
            from datetime import datetime

            run.ended_at = datetime.utcnow()

    if summary is not None:
        run.summary = summary
    if error_excerpt is not None:
        run.error_excerpt = error_excerpt

    await db.commit()
    await db.refresh(run)
    return run


# ============================================================================
# AgentSession CRUD
# ============================================================================


async def create_agent_session(
    db: AsyncSession,
    workspace_id: int,
    target_type: str,
    mode: str,
    user_prompt: str,
    target_id: Optional[int] = None,
) -> AgentSession:
    """Create a new agent session."""
    session = AgentSession(
        workspace_id=workspace_id,
        target_type=target_type,
        target_id=target_id,
        mode=mode,
        user_prompt=user_prompt,
        status="draft",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_agent_session(
    db: AsyncSession, session_id: int
) -> Optional[AgentSession]:
    """Get an agent session by ID."""
    result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    return result.scalars().first()


async def list_agent_sessions(
    db: AsyncSession, workspace_id: int, target_type: Optional[str] = None
) -> List[AgentSession]:
    """List all agent sessions, optionally filtered by target type."""
    query = select(AgentSession).where(AgentSession.workspace_id == workspace_id)
    if target_type:
        query = query.where(AgentSession.target_type == target_type)
    result = await db.execute(query.order_by(AgentSession.created_at.desc()))
    return list(result.scalars().all())


async def update_agent_session(
    db: AsyncSession,
    session_id: int,
    plan: Optional[str] = None,
    graph_diff: Optional[str] = None,
    code_diff_summary: Optional[str] = None,
    status: Optional[str] = None,
    target_id: Optional[int] = None,
) -> Optional[AgentSession]:
    """Update an agent session."""
    session = await get_agent_session(db, session_id)
    if not session:
        return None

    if plan is not None:
        session.plan = plan
    if graph_diff is not None:
        session.graph_diff = graph_diff
    if code_diff_summary is not None:
        session.code_diff_summary = code_diff_summary
    if status is not None:
        session.status = status
    if target_id is not None:
        session.target_id = target_id

    await db.commit()
    await db.refresh(session)
    return session
