"""LLM provider configuration with BYOK support."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel


class ProviderConfig(BaseModel):
    """Configuration for LLM provider (Anthropic or OpenAI)."""

    type: Literal["anthropic", "openai"] = "anthropic"
    base_url: str = "https://api.anthropic.com"
    api_key: str
    model: str = "claude-sonnet-4-20250514"

    @classmethod
    def from_env(cls) -> ProviderConfig | None:
        """
        Load provider configuration from environment variables.

        Supports BYOK (Bring Your Own Key) with fallback to internal keys.

        Environment variables:
            COPILOT_PROVIDER: "anthropic" or "openai" (default: "anthropic")
            COPILOT_API_KEY: User's API key (BYOK)
            COPILOT_MODEL: Model name override

            Fallback for Anthropic:
            INTERNAL_ANTHROPIC_LARGE_API_KEY: Internal Anthropic key
            INTERNAL_ANTHROPIC_LARGE_MODEL: Internal model name

            Fallback for OpenAI:
            OPENAI_API_KEY: OpenAI API key

        Returns:
            ProviderConfig if credentials found, None otherwise
        """
        provider = os.getenv("COPILOT_PROVIDER", "anthropic")

        if provider == "anthropic":
            api_key = os.getenv("COPILOT_API_KEY") or os.getenv(
                "INTERNAL_ANTHROPIC_LARGE_API_KEY"
            )
            if not api_key:
                return None

            model = os.getenv("COPILOT_MODEL") or os.getenv(
                "INTERNAL_ANTHROPIC_LARGE_MODEL", "claude-sonnet-4-20250514"
            )

            return cls(
                type="anthropic",
                base_url="https://api.anthropic.com",
                api_key=api_key,
                model=model,
            )

        elif provider == "openai":
            api_key = os.getenv("COPILOT_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None

            model = os.getenv("COPILOT_MODEL", "gpt-4o")

            return cls(
                type="openai",
                base_url="https://api.openai.com/v1",
                api_key=api_key,
                model=model,
            )

        return None

    def to_copilot_provider_config(self) -> dict:
        """Convert to Copilot SDK provider configuration format."""
        return {
            "type": self.type,
            "base_url": self.base_url,
            "api_key": self.api_key,
        }
