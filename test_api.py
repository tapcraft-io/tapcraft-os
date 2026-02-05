"""Simple test script to verify API endpoints work."""

import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import AsyncSessionLocal
from src.services import crud


async def test_crud():
    """Test basic CRUD operations."""
    async with AsyncSessionLocal() as db:
        print("Testing Tapcraft Domain Model CRUD operations...\n")

        # 1. Create a workspace
        print("1. Creating workspace...")
        workspace = await crud.create_workspace(
            db=db, owner_id="user123", name="Test Workspace"
        )
        print(f"   ✓ Created workspace: {workspace.id} - {workspace.name}")

        # 2. Create an app
        print("\n2. Creating app...")
        app = await crud.create_app(
            db=db,
            workspace_id=workspace.id,
            name="Email Notion Sync",
            slug="email_notion_sync",
            code_module_path="apps/email_notion_sync.py",
            description="Syncs important emails to Notion",
            category="email",
        )
        print(f"   ✓ Created app: {app.id} - {app.name}")

        # 3. Create app operations
        print("\n3. Creating app operations...")
        op1 = await crud.create_app_operation(
            db=db,
            app_id=app.id,
            name="filter_important",
            display_name="Filter Important Emails",
            code_symbol="apps.email_notion_sync.filter_important",
            config_schema=json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "min_priority": {"type": "integer", "default": 3}
                    },
                }
            ),
            description="Filter important emails from inbox",
        )
        print(f"   ✓ Created operation: {op1.id} - {op1.name}")

        op2 = await crud.create_app_operation(
            db=db,
            app_id=app.id,
            name="create_notion_page",
            display_name="Create Notion Page",
            code_symbol="apps.email_notion_sync.create_notion_page",
            config_schema=json.dumps(
                {
                    "type": "object",
                    "properties": {"database_id": {"type": "string"}},
                }
            ),
            description="Create a new page in Notion",
        )
        print(f"   ✓ Created operation: {op2.id} - {op2.name}")

        # 4. Create a graph for the workflow
        print("\n4. Creating workflow graph...")
        graph = await crud.create_graph(
            db=db,
            workspace_id=workspace.id,
            owner_type="workflow",
            owner_id=0,  # Will be updated when workflow is created
        )
        print(f"   ✓ Created graph: {graph.id}")

        # 5. Create workflow
        print("\n5. Creating workflow...")
        workflow = await crud.create_workflow(
            db=db,
            workspace_id=workspace.id,
            name="Daily Email Digest",
            slug="daily_email_digest",
            graph_id=graph.id,
            code_module_path="workflows/daily_email_digest.py",
            entrypoint_symbol="workflows.daily_email_digest.DailyDigestWorkflow",
            description="Process important emails daily",
        )
        print(f"   ✓ Created workflow: {workflow.id} - {workflow.name}")

        # 6. Create nodes
        print("\n6. Creating graph nodes...")
        trigger_node = await crud.create_node(
            db=db,
            graph_id=graph.id,
            kind="trigger",
            label="Daily Trigger",
            primitive_type="cron",
            config=json.dumps({"cron": "0 9 * * *"}),
            ui_position=json.dumps({"x": 100, "y": 100}),
        )
        print(f"   ✓ Created trigger node: {trigger_node.id}")

        filter_node = await crud.create_node(
            db=db,
            graph_id=graph.id,
            kind="app_operation",
            label="Filter Important",
            app_operation_id=op1.id,
            config=json.dumps({"min_priority": 4}),
            ui_position=json.dumps({"x": 300, "y": 100}),
        )
        print(f"   ✓ Created app operation node: {filter_node.id}")

        notion_node = await crud.create_node(
            db=db,
            graph_id=graph.id,
            kind="app_operation",
            label="Save to Notion",
            app_operation_id=op2.id,
            config=json.dumps({"database_id": "abc123"}),
            ui_position=json.dumps({"x": 500, "y": 100}),
        )
        print(f"   ✓ Created app operation node: {notion_node.id}")

        # 7. Create edges
        print("\n7. Creating graph edges...")
        edge1 = await crud.create_edge(
            db=db,
            graph_id=graph.id,
            from_node_id=trigger_node.id,
            to_node_id=filter_node.id,
            path="success",
        )
        print(f"   ✓ Created edge: {edge1.id}")

        edge2 = await crud.create_edge(
            db=db,
            graph_id=graph.id,
            from_node_id=filter_node.id,
            to_node_id=notion_node.id,
            path="success",
        )
        print(f"   ✓ Created edge: {edge2.id}")

        # 8. Update graph with entry node
        print("\n8. Updating graph entry node...")
        graph = await crud.update_graph(
            db=db, graph_id=graph.id, entry_node_id=trigger_node.id
        )
        print(f"   ✓ Updated graph entry node: {graph.entry_node_id}")

        # 9. Create a schedule
        print("\n9. Creating schedule...")
        schedule = await crud.create_schedule(
            db=db,
            workspace_id=workspace.id,
            workflow_id=workflow.id,
            name="Daily at 9am",
            cron="0 9 * * *",
            timezone="America/New_York",
        )
        print(f"   ✓ Created schedule: {schedule.id} - {schedule.name}")

        # 10. Create a run
        print("\n10. Creating run...")
        run = await crud.create_run(
            db=db,
            workspace_id=workspace.id,
            workflow_id=workflow.id,
            input_config=json.dumps({"test": True}),
        )
        print(f"   ✓ Created run: {run.id} - Status: {run.status}")

        # 11. Update run status
        print("\n11. Updating run status...")
        run = await crud.update_run(
            db=db,
            run_id=run.id,
            status="running",
            summary="Processing emails...",
        )
        print(f"   ✓ Updated run: {run.id} - Status: {run.status}")

        # 12. Create agent session
        print("\n12. Creating agent session...")
        session = await crud.create_agent_session(
            db=db,
            workspace_id=workspace.id,
            target_type="workflow",
            mode="modify",
            user_prompt="Add error handling to email filter",
            target_id=workflow.id,
        )
        print(f"   ✓ Created agent session: {session.id}")

        # 13. List operations
        print("\n13. Testing list operations...")
        apps = await crud.list_apps(db=db, workspace_id=workspace.id)
        print(f"   ✓ Found {len(apps)} apps")

        workflows = await crud.list_workflows(db=db, workspace_id=workspace.id)
        print(f"   ✓ Found {len(workflows)} workflows")

        schedules = await crud.list_schedules(db=db, workspace_id=workspace.id)
        print(f"   ✓ Found {len(schedules)} schedules")

        runs = await crud.list_runs(db=db, workspace_id=workspace.id)
        print(f"   ✓ Found {len(runs)} runs")

        # 14. Get operations with relationships
        print("\n14. Testing get operations with relationships...")
        app_with_ops = await crud.get_app(db=db, app_id=app.id, load_operations=True)
        print(f"   ✓ App has {len(app_with_ops.operations)} operations")

        workflow_with_graph = await crud.get_workflow(
            db=db, workflow_id=workflow.id, load_graph=True
        )
        print(f"   ✓ Workflow graph has {len(workflow_with_graph.graph.nodes)} nodes")
        print(f"   ✓ Workflow graph has {len(workflow_with_graph.graph.edges)} edges")

        print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_crud())
