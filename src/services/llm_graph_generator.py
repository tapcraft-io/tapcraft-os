"""LLM-based workflow graph generator using GitHub Copilot SDK."""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from copilot import CopilotClient

from src.config.llm_config import ProviderConfig
from src.models.agent_models import (
    BUILT_IN_PRIMITIVES,
    AppInfo,
    GraphSpec,
)

LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert workflow automation architect for Tapcraft.

Your job is to design workflow graphs that orchestrate app operations and primitives to accomplish user goals.

KEY PRINCIPLES:
1. **Start with a trigger**: Every workflow must begin with a trigger node (kind="trigger", primitive_type="manual" or "cron")
2. **Use available operations**: Only reference app operations that are provided in the context
3. **Linear flows first**: For v1, create simple linear flows (A -> B -> C). Branching/conditions come later.
4. **Primitives when needed**: Use HTTP requests, delays, logs, or browse when no app operation fits
5. **Meaningful labels**: Give nodes clear, action-oriented labels ("Fetch Unread Emails", not "Node 1")
6. **Logical positions**: Place nodes left-to-right in execution order (x: 100, 300, 500...)

WORKFLOW STRUCTURE:
- Nodes: Individual steps (operations or primitives)
- Edges: Connections showing flow (usually "success" path)
- Entry point: Always the trigger node

OUTPUT FORMAT:
Return a valid JSON object matching this schema:
{
  "name": "Workflow name",
  "description": "What the workflow does",
  "nodes": [
    {
      "temp_id": "trigger",
      "kind": "trigger",
      "label": "Manual Trigger",
      "primitive_type": "manual",
      "config": {},
      "ui_position": {"x": 100, "y": 200}
    }
  ],
  "edges": [
    {"from_temp_id": "trigger", "to_temp_id": "next_node", "path": "success"}
  ],
  "entry_node_temp_id": "trigger",
  "reasoning": "Your thought process"
}

EXAMPLES OF GOOD WORKFLOWS:
1. Email -> Notion: Trigger -> Fetch Emails -> Filter Important -> Create Notion Page
2. Daily Report: Cron Trigger -> Fetch Data (HTTP) -> Process -> Send Slack Message
3. Web Verification: Trigger -> Browse Page -> Verify Element -> Log Result

Think step by step and design a clean, working workflow."""


class LLMGraphGenerator:
    """Generates workflow graphs using GitHub Copilot SDK."""

    def __init__(self, config: ProviderConfig):
        """
        Initialize the LLM graph generator.

        Args:
            config: Provider configuration with BYOK credentials
        """
        self.config = config
        self._client: CopilotClient | None = None

    async def _get_client(self) -> CopilotClient:
        """Get or create the Copilot client."""
        if self._client is None:
            self._client = CopilotClient()
            await self._client.start()
        return self._client

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
        client = await self._get_client()

        session = await client.create_session({
            "model": self.config.model,
            "provider": self.config.to_copilot_provider_config(),
        })

        context = self._build_context(user_prompt, available_apps, constraints or [])
        full_prompt = f"{SYSTEM_PROMPT}\n\n{context}"

        result = await session.send_and_wait({"prompt": full_prompt})

        # Parse JSON from response
        output = result.output if hasattr(result, "output") else str(result)
        graph_data = self._extract_json(output)

        return GraphSpec.model_validate(graph_data)

    def _build_context(
        self,
        user_prompt: str,
        available_apps: List[AppInfo],
        constraints: List[str],
    ) -> str:
        """Build the context/prompt for the LLM."""
        apps_description = self._format_apps(available_apps)
        primitives_description = self._format_primitives()

        prompt = f"""USER REQUEST:
{user_prompt}

AVAILABLE APP OPERATIONS:
{apps_description}

BUILT-IN PRIMITIVES:
{primitives_description}
"""

        if constraints:
            prompt += "\nADDITIONAL CONSTRAINTS:\n" + "\n".join(
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

Return ONLY the JSON object, no markdown code blocks."""

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

                if op.config_schema and op.config_schema.get("properties"):
                    lines.append(
                        f"    - Config: {', '.join(op.config_schema['properties'].keys())}"
                    )

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

    def _extract_json(self, text: str) -> dict:
        """Extract JSON object from LLM response."""
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code block
        import re

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to find raw JSON object
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        raise ValueError(f"Could not extract JSON from response: {text[:200]}")

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


def create_graph_generator() -> LLMGraphGenerator | None:
    """
    Factory function to create a graph generator.

    Returns:
        LLMGraphGenerator instance or None if no provider configured
    """
    config = ProviderConfig.from_env()
    if not config:
        LOGGER.warning("No LLM provider configured - graph generation unavailable")
        return None

    return LLMGraphGenerator(config)
