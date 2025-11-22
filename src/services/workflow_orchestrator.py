"""Orchestrates workflow creation via agent: prompt → graph → code → execution."""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json

from src.services import crud
from src.services.code_generator import CodeGeneratorService
from src.services.git_service import GitService
from src.db.models import Workflow, Graph, Node, Edge, App, AppOperation


class WorkflowOrchestrator:
    """Orchestrates the creation of workflows via the AI agent."""

    def __init__(self):
        self.code_generator = CodeGeneratorService()
        self.git_service = GitService()

    async def create_workflow_from_prompt(
        self,
        db: AsyncSession,
        workspace_id: int,
        user_prompt: str,
        available_apps: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Create a complete workflow from a user prompt.

        Flow:
        1. Parse prompt and generate graph structure
        2. Create graph in database
        3. Generate Temporal workflow code
        4. Write code to disk
        5. Create workflow record
        6. Return workflow details

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_prompt: User's natural language description
            available_apps: Optional list of app IDs to use

        Returns:
            Dict with workflow, graph, and generation info
        """

        # 1. Create agent session
        agent_session = await crud.create_agent_session(
            db=db,
            workspace_id=workspace_id,
            target_type="workflow",
            mode="create",
            user_prompt=user_prompt,
        )

        # 2. Get available apps and operations
        apps = await crud.list_apps(db=db, workspace_id=workspace_id)
        app_operations_map = {}  # op_id -> {code_symbol, name, app_name}

        for app in apps:
            if available_apps and app.id not in available_apps:
                continue
            for op in app.operations:
                app_operations_map[op.id] = {
                    "code_symbol": op.code_symbol,
                    "name": op.name,
                    "display_name": op.display_name,
                    "app_name": app.name,
                    "config_schema": op.config_schema,
                }

        # 3. Generate graph structure from prompt
        # For now, use a simple heuristic-based approach
        # TODO: Replace with actual LLM-based generation
        graph_spec = self._generate_graph_from_prompt(
            user_prompt, app_operations_map
        )

        # 4. Create graph in database
        graph = await crud.create_graph(
            db=db,
            workspace_id=workspace_id,
            owner_type="workflow",
            owner_id=0,  # Will be updated after workflow is created
        )

        # 5. Create nodes
        node_id_map = {}  # temp_id -> db_id
        for node_spec in graph_spec["nodes"]:
            node = await crud.create_node(
                db=db,
                graph_id=graph.id,
                kind=node_spec["kind"],
                label=node_spec["label"],
                config=json.dumps(node_spec.get("config", {})),
                config_schema=node_spec.get("config_schema", "{}"),
                ui_position=json.dumps(node_spec.get("ui_position", {"x": 0, "y": 0})),
                app_operation_id=node_spec.get("app_operation_id"),
                primitive_type=node_spec.get("primitive_type"),
            )
            node_id_map[node_spec["temp_id"]] = node.id

        # 6. Create edges
        for edge_spec in graph_spec["edges"]:
            from_id = node_id_map[edge_spec["from_temp_id"]]
            to_id = node_id_map[edge_spec["to_temp_id"]]
            await crud.create_edge(
                db=db,
                graph_id=graph.id,
                from_node_id=from_id,
                to_node_id=to_id,
                path=edge_spec.get("path"),
                label=edge_spec.get("label"),
            )

        # 7. Update graph with entry node
        entry_node_temp_id = graph_spec.get("entry_node_temp_id")
        if entry_node_temp_id:
            entry_node_id = node_id_map[entry_node_temp_id]
            await crud.update_graph(db=db, graph_id=graph.id, entry_node_id=entry_node_id)

        # 8. Generate workflow name and slug
        workflow_name = graph_spec.get("name", "GeneratedWorkflow")
        workflow_slug = workflow_name.lower().replace(" ", "_")
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
            description=graph_spec.get("description", user_prompt[:200]),
        )

        # 14. Update agent session
        await crud.update_agent_session(
            db=db,
            session_id=agent_session.id,
            plan=json.dumps(graph_spec),
            code_diff_summary=f"Generated {len(workflow_code)} bytes of code",
            status="applied",
            target_id=workflow.id,
        )

        return {
            "workflow": workflow,
            "graph": graph,
            "code": workflow_code,
            "agent_session_id": agent_session.id,
        }

    def _generate_graph_from_prompt(
        self, prompt: str, app_operations: Dict[int, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Generate a graph specification from user prompt.

        For MVP, uses simple keyword matching.
        TODO: Replace with LLM-based generation.
        """

        # Simple heuristic: look for app operation names in prompt
        prompt_lower = prompt.lower()

        # Find relevant operations
        relevant_ops = []
        for op_id, op_info in app_operations.items():
            if (
                op_info["name"].lower() in prompt_lower
                or op_info["display_name"].lower() in prompt_lower
            ):
                relevant_ops.append((op_id, op_info))

        # If no ops found, create a simple HTTP request workflow
        if not relevant_ops:
            return self._generate_simple_http_workflow(prompt)

        # Build graph with trigger + operations in sequence
        nodes = []
        edges = []

        # Trigger node
        nodes.append(
            {
                "temp_id": "trigger",
                "kind": "trigger",
                "label": "Manual Trigger",
                "primitive_type": "manual",
                "config": {},
                "ui_position": {"x": 100, "y": 100},
            }
        )

        # Add operation nodes
        prev_id = "trigger"
        for idx, (op_id, op_info) in enumerate(relevant_ops):
            node_id = f"op_{idx}"
            nodes.append(
                {
                    "temp_id": node_id,
                    "kind": "app_operation",
                    "label": op_info["display_name"],
                    "app_operation_id": op_id,
                    "config": {},
                    "config_schema": op_info["config_schema"],
                    "ui_position": {"x": 300 + idx * 200, "y": 100},
                }
            )

            edges.append(
                {
                    "from_temp_id": prev_id,
                    "to_temp_id": node_id,
                    "path": "success",
                }
            )

            prev_id = node_id

        # Extract workflow name from prompt (simple heuristic)
        words = prompt.split()
        name = " ".join(words[:3]) if len(words) >= 3 else "Generated Workflow"

        return {
            "name": name.title(),
            "description": prompt,
            "nodes": nodes,
            "edges": edges,
            "entry_node_temp_id": "trigger",
        }

    def _generate_simple_http_workflow(self, prompt: str) -> Dict[str, Any]:
        """Generate a simple HTTP request workflow as fallback."""

        nodes = [
            {
                "temp_id": "trigger",
                "kind": "trigger",
                "label": "Manual Trigger",
                "primitive_type": "manual",
                "config": {},
                "ui_position": {"x": 100, "y": 100},
            },
            {
                "temp_id": "http",
                "kind": "primitive",
                "label": "HTTP Request",
                "primitive_type": "http_request",
                "config": {
                    "method": "GET",
                    "url": "https://api.example.com/data",
                },
                "ui_position": {"x": 300, "y": 100},
            },
        ]

        edges = [
            {
                "from_temp_id": "trigger",
                "to_temp_id": "http",
                "path": "success",
            }
        ]

        return {
            "name": "Simple HTTP Workflow",
            "description": prompt,
            "nodes": nodes,
            "edges": edges,
            "entry_node_temp_id": "trigger",
        }
