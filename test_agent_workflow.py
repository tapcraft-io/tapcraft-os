"""End-to-end test for agent-based workflow creation."""

import asyncio
import json
from pathlib import Path

from src.db.base import AsyncSessionLocal
from src.services import crud
from src.services.workflow_orchestrator import WorkflowOrchestrator


async def test_agent_workflow_creation():
    """Test creating a workflow via the agent."""
    print("=" * 80)
    print("Testing Agent-Based Workflow Creation")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # 1. Create workspace
        print("\n1. Creating workspace...")
        workspace = await crud.create_workspace(
            db=db, owner_id="test_user", name="Test Workspace"
        )
        print(f"   ✓ Created workspace: {workspace.id} - {workspace.name}")

        # 2. Create an activity with operations
        print("\n2. Creating activity with operations...")
        activity = await crud.create_activity(
            db=db,
            workspace_id=workspace.id,
            name="Email Processor",
            slug="email_processor",
            code_module_path="activities/email_processor.py",
            description="Process emails",
            category="email",
        )
        print(f"   ✓ Created activity: {activity.id} - {activity.name}")

        # Add operations
        op1 = await crud.create_activity_operation(
            db=db,
            activity_id=activity.id,
            name="fetch_emails",
            display_name="Fetch Emails",
            code_symbol="activities.email_processor.fetch_emails",
            config_schema=json.dumps(
                {"type": "object", "properties": {"folder": {"type": "string"}}}
            ),
            description="Fetch emails from inbox",
        )
        print(f"   ✓ Created operation: {op1.name}")

        op2 = await crud.create_activity_operation(
            db=db,
            activity_id=activity.id,
            name="analyze_sentiment",
            display_name="Analyze Sentiment",
            code_symbol="activities.email_processor.analyze_sentiment",
            config_schema=json.dumps({"type": "object"}),
            description="Analyze email sentiment",
        )
        print(f"   ✓ Created operation: {op2.name}")

        # 3. Create workflow via agent
        print("\n3. Creating workflow via agent...")
        orchestrator = WorkflowOrchestrator()

        user_prompt = "Fetch emails and analyze sentiment for important messages"

        result = await orchestrator.create_workflow_from_prompt(
            db=db,
            workspace_id=workspace.id,
            user_prompt=user_prompt,
        )

        workflow = result["workflow"]
        graph = result["graph"]
        code = result["code"]

        print(f"   ✓ Created workflow: {workflow.id} - {workflow.name}")
        print(f"   ✓ Module path: {workflow.code_module_path}")
        print(f"   ✓ Entrypoint: {workflow.entrypoint_symbol}")
        print(f"   ✓ Graph has {len(graph.nodes)} nodes, {len(graph.edges)} edges")

        # 4. Verify code was written to disk
        print("\n4. Verifying generated code...")
        workspace_path = Path(f"./workspace/workspace_{workspace.id}")
        workflow_file = workspace_path / "workflows" / f"{workflow.slug}.py"

        if workflow_file.exists():
            print(f"   ✓ Code file exists: {workflow_file}")
            file_content = workflow_file.read_text()
            print(f"   ✓ File size: {len(file_content)} bytes")

            # Check for key elements
            if "@workflow.defn" in file_content:
                print("   ✓ Contains @workflow.defn decorator")
            if "async def run" in file_content:
                print("   ✓ Contains async def run method")
            if "workflow.execute_activity" in file_content:
                print("   ✓ Contains activity execution calls")
        else:
            print(f"   ✗ Code file not found: {workflow_file}")

        # 5. Display generated code
        print("\n5. Generated Workflow Code:")
        print("-" * 80)
        print(code)
        print("-" * 80)

        # 6. Display graph structure
        print("\n6. Graph Structure:")
        print(f"   Entry node ID: {graph.entry_node_id}")
        print(f"   Nodes:")
        for node in graph.nodes:
            print(
                f"     - [{node.id}] {node.label} ({node.kind})"
                + (
                    f" -> operation {node.activity_operation_id}"
                    if node.activity_operation_id
                    else ""
                )
            )
        print(f"   Edges:")
        for edge in graph.edges:
            print(
                f"     - {edge.from_node_id} → {edge.to_node_id}"
                + (f" ({edge.path})" if edge.path else "")
            )

        # 7. List all workflows
        print("\n7. All workflows in workspace:")
        workflows = await crud.list_workflows(db=db, workspace_id=workspace.id)
        for wf in workflows:
            print(f"   - {wf.name} ({wf.slug}) - {wf.code_module_path}")

        # 8. Check Git commit
        print("\n8. Git repository status:")
        git_dir = workspace_path / ".git"
        if git_dir.exists():
            print(f"   ✓ Git repository initialized")
            import subprocess

            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"   ✓ Latest commit: {result.stdout.strip()}")
        else:
            print(f"   ✗ Git repository not found")

        print("\n" + "=" * 80)
        print("✅ Agent workflow creation test completed!")
        print("=" * 80)

        return workflow


async def test_simple_http_workflow():
    """Test creating a simple HTTP workflow when no activities are available."""
    print("\n" + "=" * 80)
    print("Testing Simple HTTP Workflow (Fallback)")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # Create workspace
        workspace = await crud.create_workspace(
            db=db, owner_id="test_user_2", name="HTTP Test Workspace"
        )

        orchestrator = WorkflowOrchestrator()

        user_prompt = "Make an HTTP request to fetch weather data"

        result = await orchestrator.create_workflow_from_prompt(
            db=db,
            workspace_id=workspace.id,
            user_prompt=user_prompt,
        )

        workflow = result["workflow"]
        code = result["code"]

        print(f"\n✓ Created HTTP workflow: {workflow.name}")
        print(f"✓ Code preview:")
        print("-" * 80)
        print(code[:500] + "..." if len(code) > 500 else code)
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(test_agent_workflow_creation())
    asyncio.run(test_simple_http_workflow())
