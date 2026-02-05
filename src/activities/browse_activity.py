"""Browser automation activity using Copilot SDK with Playwright MCP."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from temporalio import activity

from src.config.llm_config import ProviderConfig

LOGGER = logging.getLogger(__name__)


@activity.defn(name="browse_page")
async def browse_page(url: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Temporal activity that uses Copilot SDK with Playwright MCP for browser automation.

    This activity is called at RUNTIME when a workflow needs to browse a page,
    verify content, take screenshots, or interact with web elements.

    Args:
        url: The URL to navigate to
        actions: List of browser actions to perform. Each action is a dict with:
            - type: "navigate" | "click" | "type" | "verify" | "screenshot" | "evaluate"
            - selector: CSS selector for the target element (for click, type, verify)
            - value: Value to type or verify against
            - name: Screenshot filename (for screenshot action)
            - script: JavaScript to evaluate (for evaluate action)

    Returns:
        dict with:
            - success: bool indicating if all actions completed
            - output: Agent's response/summary
            - screenshots: List of screenshot filenames taken
            - extracted_data: Any data extracted via evaluate actions
            - error: Error message if failed

    Example:
        await browse_page(
            url="https://example.com/status",
            actions=[
                {"type": "verify", "selector": ".status-badge", "value": "Active"},
                {"type": "screenshot", "name": "status-verification.png"},
                {"type": "click", "selector": "button.refresh"},
            ]
        )
    """
    config = ProviderConfig.from_env()
    if not config:
        return {
            "success": False,
            "error": "No LLM provider configured",
            "output": None,
            "screenshots": [],
            "extracted_data": {},
        }

    try:
        from copilot import CopilotClient

        client = CopilotClient()
        await client.start()

        session = await client.create_session({
            "model": config.model,
            "provider": config.to_copilot_provider_config(),
            "mcp_servers": {
                "playwright": {
                    "type": "local",
                    "command": "npx",
                    "args": ["@anthropic/mcp-playwright"],
                    "tools": ["*"],
                }
            }
        })

        # Build the task prompt
        task = _build_browse_task(url, actions)

        LOGGER.info(f"Starting browse activity for {url} with {len(actions)} actions")
        result = await session.send_and_wait({"prompt": task})

        output = result.output if hasattr(result, "output") else str(result)

        LOGGER.info(f"Browse activity completed for {url}")
        return {
            "success": True,
            "output": output,
            "screenshots": _extract_screenshots(actions),
            "extracted_data": {},
            "error": None,
        }

    except Exception as e:
        LOGGER.error(f"Browse activity failed for {url}: {e}")
        return {
            "success": False,
            "output": None,
            "screenshots": [],
            "extracted_data": {},
            "error": str(e),
        }


def _build_browse_task(url: str, actions: List[Dict[str, Any]]) -> str:
    """Build the task prompt for the browser agent."""
    action_descriptions = []

    for i, action in enumerate(actions, 1):
        action_type = action.get("type", "unknown")

        if action_type == "navigate":
            action_descriptions.append(f"{i}. Navigate to {action.get('url', url)}")
        elif action_type == "click":
            action_descriptions.append(
                f"{i}. Click on element: {action.get('selector', 'unknown')}"
            )
        elif action_type == "type":
            action_descriptions.append(
                f"{i}. Type '{action.get('value', '')}' into element: {action.get('selector', 'unknown')}"
            )
        elif action_type == "verify":
            action_descriptions.append(
                f"{i}. Verify that element '{action.get('selector', 'unknown')}' "
                f"contains text: '{action.get('value', '')}'"
            )
        elif action_type == "screenshot":
            action_descriptions.append(
                f"{i}. Take a screenshot and save as: {action.get('name', 'screenshot.png')}"
            )
        elif action_type == "evaluate":
            action_descriptions.append(
                f"{i}. Run JavaScript: {action.get('script', '')}"
            )
        else:
            action_descriptions.append(f"{i}. {action_type}: {action}")

    actions_text = "\n".join(action_descriptions)

    return f"""Navigate to {url} and perform the following actions:

{actions_text}

After completing all actions, summarize what you found and whether all verifications passed.
If any action fails, report the failure and stop."""


def _extract_screenshots(actions: List[Dict[str, Any]]) -> List[str]:
    """Extract screenshot filenames from actions."""
    return [
        action.get("name", "screenshot.png")
        for action in actions
        if action.get("type") == "screenshot"
    ]
