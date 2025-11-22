"""Orchestrates workflow creation via agent: prompt → LLM → graph → code → execution."""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

from src.services import crud
from src.services.code_generator import CodeGeneratorService
from src.services.git_service import GitService
from src.services.llm_graph_generator import create_graph_generator
from src.models.agent_models import AppInfo, OperationInfo, GraphSpec
from src.db.models import Workflow, Graph, Node, Edge, App, AppOperation

LOGGER = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates the creation of workflows via the AI agent."""

    def __init__(self, use_llm: bool = True):
        """
        Initialize orchestrator.

        Args:
            use_llm: If True, use LLM for graph generation. If False, use simple heuristics (for testing)
        """
        self.code_generator = CodeGeneratorService()
        self.git_service = GitService()
        self.use_llm = use_llm

        if use_llm:
            self.graph_generator = create_graph_generator()
        else:
            self.graph_generator = None

    async def create_workflow_from_prompt(
        self,
        db: AsyncSession,
        workspace_id: int,
        user_prompt: str,
        available_apps: Optional[List[int]] = None,
        constraints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a complete workflow from a user prompt using LLM.

        Flow:
        1. Load available apps and operations from database
        2. Call LLM to generate graph structure
        3. Create graph in database
        4. Generate Temporal workflow code
        5. Write code to disk and commit to Git
        6. Create workflow record
        7. Return workflow details

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_prompt: User's natural language description
            available_apps: Optional list of app IDs to use
            constraints: Optional additional constraints for LLM

        Returns:
            Dict with workflow, graph, code, and agent session info
        """

        LOGGER.info(f"Creating workflow from prompt: {user_prompt[:100]}...")

        # 1. Create agent session to track this generation
        agent_session = await crud.create_agent_session(
            db=db,
            workspace_id=workspace_id,
            target_type="workflow",
            mode="create",
            user_prompt=user_prompt,
        )

        try:
            # 2. Get available apps and operations
            apps = await crud.list_apps(db=db, workspace_id=workspace_id)

            # Build app info for LLM
            app_info_list: List[AppInfo] = []
            app_operations_map = {}  # op_id -> {code_symbol, name, ...}

            for app in apps:
                if available_apps and app.id not in available_apps:
                    continue

                operations = []
                for op in app.operations:
                    # Store for code generation later
                    app_operations_map[op.id] = {
                        "code_symbol": op.code_symbol,
                        "name": op.name,
                        "display_name": op.display_name,
                        "app_name": app.name,
                        "config_schema": op.config_schema,
                    }

                    # Build operation info for LLM
                    try:
                        config_schema = (
                            json.loads(op.config_schema)
                            if isinstance(op.config_schema, str)
                            else op.config_schema
                        )
                    except:
                        config_schema = {}

                    operations.append(
                        OperationInfo(
                            id=op.id,
                            name=op.name,
                            display_name=op.display_name,
                            description=op.description,
                            config_schema=config_schema,
                        )
                    )

                app_info_list.append(
                    AppInfo(
                        id=app.id,
                        name=app.name,
                        description=app.description,
                        category=app.category,
                        operations=operations,
                    )
                )

            LOGGER.info(f"Found {len(app_info_list)} apps with {len(app_operations_map)} operations")

            # 3. Generate graph structure using LLM or fallback
            if self.use_llm and self.graph_generator:
                LOGGER.info("Generating graph via LLM...")
                graph_spec = await self.graph_generator.generate_graph(
                    user_prompt=user_prompt,
                    available_apps=app_info_list,
                    constraints=constraints,
                )
                LOGGER.info(
                    f"LLM generated workflow '{graph_spec.name}' with {len(graph_spec.nodes)} nodes"
                )
            else:
                LOGGER.info("Using fallback heuristic graph generation...")
                graph_spec = self._generate_graph_fallback(user_prompt, app_operations_map)

            # 4. Create graph in database
            graph = await crud.create_graph(
                db=db,
                workspace_id=workspace_id,
                owner_type="workflow",
                owner_id=0,  # Will be updated after workflow is created
            )

            # 5. Create nodes
            node_id_map = {}  # temp_id -> db_id
            for node_spec in graph_spec.nodes:
                node = await crud.create_node(
                    db=db,
                    graph_id=graph.id,
                    kind=node_spec.kind,
                    label=node_spec.label,
                    config=json.dumps(node_spec.config),
                    config_schema=json.dumps({}),  # TODO: get from operation
                    ui_position=json.dumps(node_spec.ui_position),
                    app_operation_id=node_spec.app_operation_id,
                    primitive_type=node_spec.primitive_type,
                )
                node_id_map[node_spec.temp_id] = node.id

            # 6. Create edges
            for edge_spec in graph_spec.edges:
                from_id = node_id_map[edge_spec.from_temp_id]
                to_id = node_id_map[edge_spec.to_temp_id]
                await crud.create_edge(
                    db=db,
                    graph_id=graph.id,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    path=edge_spec.path,
                    label=edge_spec.label,
                )

            # 7. Update graph with entry node
            if graph_spec.entry_node_temp_id:
                entry_node_id = node_id_map[graph_spec.entry_node_temp_id]
                await crud.update_graph(db=db, graph_id=graph.id, entry_node_id=entry_node_id)

            # 8. Generate workflow name and slug
            workflow_name = graph_spec.name
            workflow_slug = workflow_name.lower().replace(" ", "_").replace("-", "_")
            workflow_class_name = "".join(word.capitalize() for word in workflow_name.split())

            # 9. Refresh graph with nodes and edges
            graph = await crud.get_graph(db=db, graph_id=graph.id, load_nodes_edges=True)

            # 10. Generate Temporal workflow code
            graph_data = {
                "nodes": [
                    {
                        "id": n.id,
                        "kind": n.kind,
                        "label": n.label,
                        "config": n.config,
                        "app_operation_id": n.app_operation_id,
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

            workflow_code = self.code_generator.generate_workflow_from_graph(
                workflow_name=workflow_class_name,
                graph_data=graph_data,
                app_operations=app_operations_map,
            )

            # 11. Write code to disk
            code_module_path = self.git_service.write_workflow_code(
                workspace_id=workspace_id,
                workflow_slug=workflow_slug,
                code=workflow_code,
            )

            # 12. Commit to git
            self.git_service.commit_changes(
                workspace_id=workspace_id,
                message=f"Create workflow: {workflow_name}\n\nGenerated from prompt: {user_prompt[:100]}",
            )

            # 13. Create workflow record
            entrypoint_symbol = f"{code_module_path}.{workflow_class_name}"
            workflow = await crud.create_workflow(
                db=db,
                workspace_id=workspace_id,
                name=workflow_name,
                slug=workflow_slug,
                graph_id=graph.id,
                code_module_path=code_module_path,
                entrypoint_symbol=entrypoint_symbol,
                description=graph_spec.description,
            )

            # 14. Update agent session with results
            plan_data = {
                "graph_spec": graph_spec.model_dump(),
                "reasoning": graph_spec.reasoning,
                "complexity": graph_spec.estimated_complexity,
            }

            await crud.update_agent_session(
                db=db,
                session_id=agent_session.id,
                plan=json.dumps(plan_data),
                code_diff_summary=f"Generated {len(workflow_code)} bytes of code with {len(graph_spec.nodes)} nodes",
                status="applied",
                target_id=workflow.id,
            )

            LOGGER.info(f"Successfully created workflow {workflow.id}: {workflow.name}")

            return {
                "workflow": workflow,
                "graph": graph,
                "code": workflow_code,
                "agent_session_id": agent_session.id,
                "graph_spec": graph_spec,
            }

        except Exception as e:
            LOGGER.error(f"Failed to create workflow: {e}", exc_info=True)
            # Update agent session as rejected
            await crud.update_agent_session(
                db=db,
                session_id=agent_session.id,
                status="rejected",
                code_diff_summary=f"Error: {str(e)}",
            )
            raise

    def _generate_graph_fallback(
        self, prompt: str, app_operations: Dict[int, Dict[str, str]]
    ) -> GraphSpec:
        """
        Simple fallback graph generation (for testing without LLM).

        Creates a basic linear workflow.
        """
        from src.models.agent_models import NodeSpec, EdgeSpec, GraphSpec

        # Simple heuristic: look for app operation names in prompt
        prompt_lower = prompt.lower()

        relevant_ops = []
        for op_id, op_info in app_operations.items():
            if (
                op_info["name"].lower() in prompt_lower
                or op_info["display_name"].lower() in prompt_lower
            ):
                relevant_ops.append((op_id, op_info))

        # If no ops found, create HTTP workflow
        if not relevant_ops:
            return GraphSpec(
                name="Simple HTTP Workflow",
                description=prompt,
                nodes=[
                    NodeSpec(
                        temp_id="trigger",
                        kind="trigger",
                        label="Manual Trigger",
                        primitive_type="manual",
                        config={},
                        ui_position={"x": 100, "y": 100},
                    ),
                    NodeSpec(
                        temp_id="http",
                        kind="primitive",
                        label="HTTP Request",
                        primitive_type="http_request",
                        config={"method": "GET", "url": "https://api.example.com/data"},
                        ui_position={"x": 300, "y": 100},
                    ),
                ],
                edges=[
                    EdgeSpec(from_temp_id="trigger", to_temp_id="http", path="success")
                ],
                entry_node_temp_id="trigger",
                reasoning="Fallback: No matching app operations found, created simple HTTP workflow",
            )

        # Create linear workflow with found operations
        nodes = [
            NodeSpec(
                temp_id="trigger",
                kind="trigger",
                label="Manual Trigger",
                primitive_type="manual",
                config={},
                ui_position={"x": 100, "y": 100},
            )
        ]

        edges = []
        prev_id = "trigger"

        for idx, (op_id, op_info) in enumerate(relevant_ops):
            node_id = f"op_{idx}"
            nodes.append(
                NodeSpec(
                    temp_id=node_id,
                    kind="app_operation",
                    label=op_info["display_name"],
                    app_operation_id=op_id,
                    config={},
                    ui_position={"x": 300 + idx * 200, "y": 100},
                )
            )

            edges.append(
                EdgeSpec(from_temp_id=prev_id, to_temp_id=node_id, path="success")
            )
            prev_id = node_id

        name = " ".join(prompt.split()[:3]).title() if len(prompt.split()) >= 3 else "Generated Workflow"

        return GraphSpec(
            name=name,
            description=prompt,
            nodes=nodes,
            edges=edges,
            entry_node_temp_id="trigger",
            reasoning="Fallback: Simple keyword matching to find operations",
        )
