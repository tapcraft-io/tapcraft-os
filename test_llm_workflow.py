"""Test LLM-based workflow generation."""

import asyncio
import os
from pathlib import Path

from src.db.base import AsyncSessionLocal
from src.services import crud
from src.services.workflow_orchestrator import WorkflowOrchestrator


async def test_llm_workflow_generation():
    """Test creating workflows with LLM."""

    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Using fallback mode (no LLM).")
        print("   Set OPENAI_API_KEY in .env to test real LLM generation.\n")
        use_llm = False
    else:
        print("✓ OPENAI_API_KEY found. Using LLM for workflow generation.\n")
        use_llm = True

    print("=" * 80)
    print("Testing LLM-Based Workflow Generation")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # 1. Create workspace
        print("\n1. Setting up workspace...")
        workspace = await crud.create_workspace(
            db=db, owner_id="llm_test_user", name="LLM Test Workspace"
        )
        print(f"   ✓ Created workspace: {workspace.id}")

        # 2. Create activities with operations
        print("\n2. Creating sample activities...")

        # Email activity
        email_activity = await crud.create_activity(
            db=db,
            workspace_id=workspace.id,
            name="Email Client",
            slug="email_client",
            code_module_path="activities/email_client.py",
            description="Connect to email providers and process messages",
            category="email",
        )

        await crud.create_activity_operation(
            db=db,
            activity_id=email_activity.id,
            name="fetch_unread",
            display_name="Fetch Unread Emails",
            code_symbol="activities.email_client.fetch_unread",
            config_schema='{"type": "object", "properties": {"folder": {"type": "string", "default": "INBOX"}}}',
            description="Fetch all unread emails from a specific folder",
        )

        await crud.create_activity_operation(
            db=db,
            activity_id=email_activity.id,
            name="mark_as_read",
            display_name="Mark as Read",
            code_symbol="activities.email_client.mark_as_read",
            config_schema='{"type": "object", "properties": {"email_ids": {"type": "array"}}}',
            description="Mark specific emails as read",
        )

        # Slack activity
        slack_activity = await crud.create_activity(
            db=db,
            workspace_id=workspace.id,
            name="Slack Messenger",
            slug="slack",
            code_module_path="activities/slack.py",
            description="Send messages and notifications to Slack",
            category="messaging",
        )

        await crud.create_activity_operation(
            db=db,
            activity_id=slack_activity.id,
            name="send_message",
            display_name="Send Slack Message",
            code_symbol="activities.slack.send_message",
            config_schema='{"type": "object", "properties": {"channel": {"type": "string"}, "text": {"type": "string"}}, "required": ["channel", "text"]}',
            description="Send a message to a Slack channel",
        )

        # Notion activity
        notion_activity = await crud.create_activity(
            db=db,
            workspace_id=workspace.id,
            name="Notion Database",
            slug="notion",
            code_module_path="activities/notion.py",
            description="Create and update Notion pages and databases",
            category="productivity",
        )

        await crud.create_activity_operation(
            db=db,
            activity_id=notion_activity.id,
            name="create_page",
            display_name="Create Notion Page",
            code_symbol="activities.notion.create_page",
            config_schema='{"type": "object", "properties": {"database_id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}}}',
            description="Create a new page in a Notion database",
        )

        print(f"   ✓ Created {email_activity.name} with 2 operations")
        print(f"   ✓ Created {slack_activity.name} with 1 operation")
        print(f"   ✓ Created {notion_activity.name} with 1 operation")

        # 3. Test different workflow prompts
        test_prompts = [
            {
                "name": "Simple Email to Slack",
                "prompt": "Every morning, fetch my unread emails and send a count to Slack #general channel",
                "expected": "Should use fetch_unread + send_message with trigger"
            },
            {
                "name": "Email to Notion Archive",
                "prompt": "Get unread emails, create a Notion page for each one with the subject and body, then mark them as read",
                "expected": "Should use fetch_unread → create_page → mark_as_read"
            },
            {
                "name": "Complex Multi-Step",
                "prompt": "Fetch unread emails, save important ones to Notion, send a summary to Slack, and mark all as read",
                "expected": "Should orchestrate all 4 operations in sequence"
            },
        ]

        orchestrator = WorkflowOrchestrator(use_llm=use_llm)

        for idx, test in enumerate(test_prompts, 1):
            print(f"\n{'=' * 80}")
            print(f"TEST {idx}: {test['name']}")
            print(f"{'=' * 80}")
            print(f"Prompt: {test['prompt']}")
            print(f"Expected: {test['expected']}\n")

            try:
                result = await orchestrator.create_workflow_from_prompt(
                    db=db,
                    workspace_id=workspace.id,
                    user_prompt=test['prompt'],
                )

                workflow = result["workflow"]
                graph_spec = result.get("graph_spec")

                print(f"✓ Generated workflow: {workflow.name}")
                print(f"  Description: {workflow.description[:100]}...")
                print(f"  Nodes: {len(graph_spec.nodes)}")
                print(f"  Edges: {len(graph_spec.edges)}")

                if graph_spec.reasoning:
                    print(f"  LLM Reasoning: {graph_spec.reasoning[:150]}...")

                print(f"\n  Node Details:")
                for node in graph_spec.nodes:
                    symbol = f"→ op {node.activity_operation_id}" if node.activity_operation_id else ""
                    symbol = symbol or (f"→ {node.primitive_type}" if node.primitive_type else "")
                    print(f"    [{node.temp_id}] {node.label} ({node.kind}){symbol}")

                print(f"\n  Edge Flow:")
                for edge in graph_spec.edges:
                    print(f"    {edge.from_temp_id} → {edge.to_temp_id} ({edge.path or 'success'})")

                # Verify code was generated
                workspace_path = Path(f"./workspace/workspace_{workspace.id}")
                workflow_file = workspace_path / "workflows" / f"{workflow.slug}.py"
                if workflow_file.exists():
                    code_size = len(workflow_file.read_text())
                    print(f"\n  ✓ Code generated: {code_size} bytes")
                else:
                    print(f"\n  ✗ Code file not found!")

            except Exception as e:
                print(f"✗ Failed: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n{'=' * 80}")
        print("✅ All workflow generation tests completed!")
        print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(test_llm_workflow_generation())
