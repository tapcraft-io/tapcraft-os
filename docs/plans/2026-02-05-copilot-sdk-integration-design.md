# GitHub Copilot SDK Integration Design

**Date:** 2026-02-05
**Status:** Approved

## Overview

Replace all LLM-based code in tapcraft-os with the GitHub Copilot SDK, supporting BYOK (Bring Your Own Key) for both Anthropic and OpenAI providers. Add Playwright MCP as a browsing activity for workflows.

## Goals

1. Replace `LLMGraphGenerator` and `AgentService` with Copilot SDK
2. Support BYOK for Anthropic and OpenAI providers
3. Add `browse_page` as a Temporal activity using Playwright MCP
4. Keep graph generation separate from MCP (MCP only needed at runtime for browsing)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      DESIGN TIME                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           Graph Generator (Copilot SDK)               │ │
│  │  - Takes: user prompt + available activities          │ │
│  │  - Outputs: GraphSpec (nodes, edges)                  │ │
│  │  - No MCP - just structured output from LLM           │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      RUNTIME                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           Temporal Workflow Execution                 │ │
│  │                                                       │ │
│  │   Activity 1: send_email(...)                         │ │
│  │        ↓                                              │ │
│  │   Activity 2: browse_page(url, actions)  ← MCP here   │ │
│  │        ↓                                              │ │
│  │   Activity 3: log_result(...)                         │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Technical Stack

| Component | Purpose |
|-----------|---------|
| GitHub Copilot SDK | Agent framework with native MCP + BYOK |
| BYOK | Built-in support for Anthropic & OpenAI |
| MCP Servers | Local (stdio) for Playwright browsing |
| Temporal | Workflow orchestration |

## Implementation Details

### 1. Provider Configuration (BYOK)

New file: `src/config/llm_config.py`

```python
from pydantic import BaseModel
from typing import Literal

class ProviderConfig(BaseModel):
    type: Literal["anthropic", "openai"] = "anthropic"
    base_url: str = "https://api.anthropic.com"
    api_key: str
    model: str = "claude-sonnet-4-20250514"

    @classmethod
    def from_env(cls) -> "ProviderConfig | None":
        import os

        provider = os.getenv("COPILOT_PROVIDER", "anthropic")

        if provider == "anthropic":
            api_key = os.getenv("COPILOT_API_KEY") or os.getenv("INTERNAL_ANTHROPIC_LARGE_API_KEY")
            if not api_key:
                return None
            return cls(
                type="anthropic",
                base_url="https://api.anthropic.com",
                api_key=api_key,
                model=os.getenv("COPILOT_MODEL", "claude-sonnet-4-20250514")
            )
        elif provider == "openai":
            api_key = os.getenv("COPILOT_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            return cls(
                type="openai",
                base_url="https://api.openai.com/v1",
                api_key=api_key,
                model=os.getenv("COPILOT_MODEL", "gpt-4o")
            )

        return None
```

### 2. Graph Generator

Replace `src/services/llm_graph_generator.py`:

```python
from copilot import CopilotClient
from src.models.agent_models import GraphSpec, AppInfo
from src.config.llm_config import ProviderConfig

class GraphGenerator:
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = CopilotClient()

    async def generate(self, prompt: str, apps: list[AppInfo]) -> GraphSpec:
        await self.client.start()

        session = await self.client.create_session({
            "model": self.config.model,
            "provider": {
                "type": self.config.type,
                "base_url": self.config.base_url,
                "api_key": self.config.api_key,
            }
        })

        context = self._build_context(prompt, apps)
        result = await session.send_and_wait({"prompt": context})

        return GraphSpec.model_validate_json(result.output)

    def _build_context(self, prompt: str, apps: list[AppInfo]) -> str:
        # Build context with available apps/activities
        # Similar to existing _build_context in llm_graph_generator.py
        pass
```

### 3. Browse Activity (Playwright MCP)

New file: `src/activities/browse_activity.py`

```python
from temporalio import activity
from copilot import CopilotClient
from src.config.llm_config import ProviderConfig

@activity.defn
async def browse_page(url: str, actions: list[dict]) -> dict:
    """
    Temporal activity that uses Copilot SDK with Playwright MCP.

    Args:
        url: The URL to navigate to
        actions: List of browser actions to perform
            - {"type": "verify", "selector": ".status", "value": "Active"}
            - {"type": "screenshot", "name": "verification.png"}
            - {"type": "click", "selector": "button.submit"}
            - {"type": "type", "selector": "input.email", "value": "test@example.com"}

    Returns:
        dict with success status and output/screenshots
    """
    config = ProviderConfig.from_env()
    if not config:
        return {"success": False, "error": "No LLM provider configured"}

    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": config.model,
        "provider": {
            "type": config.type,
            "base_url": config.base_url,
            "api_key": config.api_key,
        },
        "mcp_servers": {
            "playwright": {
                "type": "local",
                "command": "npx",
                "args": ["@anthropic/mcp-playwright"],
                "tools": ["*"],
            }
        }
    })

    task = f"Navigate to {url} and perform these actions: {actions}"
    result = await session.send_and_wait({"prompt": task})

    return {"success": True, "output": result.output}
```

### 4. Register Browse as Primitive

Add to `src/models/agent_models.py` BUILT_IN_PRIMITIVES:

```python
PrimitiveInfo(
    type="browse",
    name="Browse Page",
    description="Navigate to a URL and perform browser actions (click, type, verify, screenshot)",
    example_config={
        "url": "https://example.com",
        "actions": [
            {"type": "verify", "selector": ".status", "value": "Active"},
            {"type": "screenshot", "name": "verification.png"}
        ]
    }
)
```

### 5. Update AgentService

Simplify `src/services/agent_service.py` to use the new GraphGenerator instead of building modules directly.

## Files to Change

| File | Action |
|------|--------|
| `src/services/llm_graph_generator.py` | Replace with Copilot SDK version |
| `src/services/agent_service.py` | Simplify to use new GraphGenerator |
| `src/activities/browse_activity.py` | **New** - Playwright MCP activity |
| `src/activities/__init__.py` | Export browse_page |
| `src/models/agent_models.py` | Add browse primitive |
| `src/config/llm_config.py` | **New** - BYOK provider config |
| `src/worker/worker.py` | Register browse_page activity |
| `pyproject.toml` | Add `github-copilot-sdk` dependency |
| `docker-compose.yml` | Add COPILOT_* env vars |

## Environment Variables

```bash
# BYOK Configuration
COPILOT_PROVIDER=anthropic  # or "openai"
COPILOT_API_KEY=sk-...      # User's API key
COPILOT_MODEL=claude-sonnet-4-20250514  # Optional model override

# Fallback (existing)
INTERNAL_ANTHROPIC_LARGE_API_KEY=...
INTERNAL_ANTHROPIC_LARGE_MODEL=...
```

## Dependencies

Add to `pyproject.toml`:

```toml
[tool.poetry.dependencies]
github-copilot-sdk = "^1.0"
```

## Testing

1. Unit tests for ProviderConfig.from_env() with various env configurations
2. Integration test for GraphGenerator with mock Copilot client
3. Integration test for browse_page activity with Playwright MCP
4. E2E test: Create a workflow that includes a browse step

## Migration Notes

- Existing workflows will continue to work (no schema changes)
- Graph generation output format (GraphSpec) remains unchanged
- API endpoints remain unchanged, only backend implementation changes
