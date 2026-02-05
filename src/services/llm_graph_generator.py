"""LLM-based workflow graph generator using pydantic-ai."""

import os
import json
from typing import List, Dict, Any, Optional
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from src.models.agent_models import (
    GraphSpec,
    NodeSpec,
    EdgeSpec,
    AppInfo,
    OperationInfo,
    PrimitiveInfo,
    BUILT_IN_PRIMITIVES,
)


class LLMGraphGenerator:
    """Generates workflow graphs using LLM with structured outputs."""

    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize the LLM graph generator.

        Args:
            model_name: OpenAI model to use (gpt-4o, gpt-4o-mini, etc.)
        """
        self.model_name = model_name
        self.model = OpenAIModel(model_name)

        # Create pydantic-ai agent with structured output
        self.agent = Agent(
            self.model,
            result_type=GraphSpec,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the graph generation agent."""
        return """You are an expert workflow automation architect for Tapcraft.

Your job is to design workflow graphs that orchestrate app operations and primitives to accomplish user goals.

KEY PRINCIPLES:
1. **Start with a trigger**: Every workflow must begin with a trigger node (kind="trigger", primitive_type="manual" or "cron")
2. **Use available operations**: Only reference app operations that are provided in the context
3. **Linear flows first**: For v1, create simple linear flows (A → B → C). Branching/conditions come later.
4. **Primitives when needed**: Use HTTP requests, delays, or logs when no app operation fits
5. **Meaningful labels**: Give nodes clear, action-oriented labels ("Fetch Unread Emails", not "Node 1")
6. **Logical positions**: Place nodes left-to-right in execution order (x: 100, 300, 500...)

WORKFLOW STRUCTURE:
- Nodes: Individual steps (operations or primitives)
- Edges: Connections showing flow (usually "success" path)
- Entry point: Always the trigger node

OUTPUT FORMAT:
Return a complete GraphSpec with:
- name: Clear workflow name
- description: What the workflow does
- nodes: All nodes including trigger
- edges: All connections
- entry_node_temp_id: Points to trigger
- reasoning: Your thought process

EXAMPLES OF GOOD WORKFLOWS:
1. Email → Notion: Trigger → Fetch Emails → Filter Important → Create Notion Page
2. Daily Report: Cron Trigger → Fetch Data (HTTP) → Process → Send Slack Message
3. Backup Workflow: Trigger → Read Files → Upload to S3 → Log Success

Think step by step and design a clean, working workflow."""

    async def generate_graph(
        self,
        user_prompt: str,
        available_apps: List[AppInfo],
        constraints: Optional[List[str]] = None,
    ) -> GraphSpec:
        """
        Generate a workflow graph from a user prompt.

        Args:
            user_prompt: Natural language description of desired workflow
            available_apps: Available apps with their operations
            constraints: Additional constraints or requirements

        Returns:
            GraphSpec: Complete workflow graph specification
        """

        # Build context about available capabilities
        context = self._build_context(user_prompt, available_apps, constraints or [])

        # Call LLM with structured output
        result = await self.agent.run(context)

        return result.data

    def _build_context(
        self,
        user_prompt: str,
        available_apps: List[AppInfo],
        constraints: List[str],
    ) -> str:
        """Build the context/prompt for the LLM."""

        # Format available apps
        apps_description = self._format_apps(available_apps)

        # Format primitives
        primitives_description = self._format_primitives()

        # Build full prompt
        prompt = f"""USER REQUEST:
{user_prompt}

AVAILABLE APP OPERATIONS:
{apps_description}

BUILT-IN PRIMITIVES:
{primitives_description}
"""

        if constraints:
            prompt += f"\nADDITIONAL CONSTRAINTS:\n" + "\n".join(
                f"- {c}" for c in constraints
            )

        prompt += """

TASK:
Design a complete workflow graph that fulfills the user's request using the available operations and primitives.

Remember:
- Start with a trigger node
- Use temp_ids that are descriptive (e.g., "trigger", "fetch_emails", "analyze")
- Set ui_position for left-to-right flow
- Include all required config for nodes that need it
- Connect nodes with edges (usually path="success")
"""

        return prompt

    def _format_apps(self, apps: List[AppInfo]) -> str:
        """Format app operations for the prompt."""
        if not apps:
            return "(No apps available - use primitives only)"

        lines = []
        for app in apps:
            lines.append(f"\n**{app.name}** ({app.category or 'general'})")
            if app.description:
                lines.append(f"  Description: {app.description}")

            for op in app.operations:
                lines.append(f"\n  Operation: {op.display_name}")
                lines.append(f"    - ID: {op.id}")
                lines.append(f"    - Name: {op.name}")
                if op.description:
                    lines.append(f"    - Description: {op.description}")

                # Show config schema if available
                try:
                    schema = json.loads(op.config_schema) if isinstance(op.config_schema, str) else op.config_schema
                    if schema.get("properties"):
                        lines.append(f"    - Config: {', '.join(schema['properties'].keys())}")
                except:
                    pass

        return "\n".join(lines)

    def _format_primitives(self) -> str:
        """Format built-in primitives for the prompt."""
        lines = []
        for prim in BUILT_IN_PRIMITIVES:
            lines.append(f"\n**{prim.name}** (type: {prim.type})")
            lines.append(f"  Description: {prim.description}")

            if prim.example_config:
                lines.append(
                    f"  Example config: {json.dumps(prim.example_config, indent=2)}"
                )

        return "\n".join(lines)

    def generate_graph_sync(
        self,
        user_prompt: str,
        available_apps: List[AppInfo],
        constraints: Optional[List[str]] = None,
    ) -> GraphSpec:
        """
        Synchronous wrapper for generate_graph.

        Args:
            user_prompt: Natural language description
            available_apps: Available apps with operations
            constraints: Additional constraints

        Returns:
            GraphSpec: Complete workflow graph
        """
        import asyncio

        return asyncio.run(
            self.generate_graph(user_prompt, available_apps, constraints)
        )


def create_graph_generator(
    model_name: Optional[str] = None,
) -> LLMGraphGenerator:
    """
    Factory function to create a graph generator.

    Args:
        model_name: Optional model name override (defaults to env or gpt-4o)

    Returns:
        LLMGraphGenerator instance
    """
    model = model_name or os.getenv("TAPCRAFT_GRAPH_MODEL", "gpt-4o")
    return LLMGraphGenerator(model_name=model)
