"""Capability caching and schema utilities."""

from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional

from src.models.core import Capability


class CapabilitiesService:
    """In-memory cache for built-in and discovered capabilities."""

    def __init__(
        self,
        builtin_capabilities: Iterable[Capability],
        ttl_seconds: int = 600,
    ) -> None:
        self._builtin_capabilities = list(builtin_capabilities)
        self._ttl_seconds = ttl_seconds
        self._cache: List[Capability] = []
        self._cache_expiry: float = 0.0

    def list_capabilities(self, force_refresh: bool = False) -> List[Capability]:
        """Return cached capabilities, optionally forcing a refresh."""

        now = time.time()
        if force_refresh or now >= self._cache_expiry or not self._cache:
            self._cache = self._load_capabilities()
            self._cache_expiry = now + self._ttl_seconds
        return list(self._cache)

    def refresh(self) -> List[Capability]:
        """Force a cache rebuild and return the updated list."""

        return self.list_capabilities(force_refresh=True)

    def get_schema(self, tool_id: str) -> Optional[Dict[str, Dict[str, object]]]:
        """Return the parameter and return schema for a tool, if known."""

        for capability in self.list_capabilities():
            if capability.id == tool_id:
                return {
                    "params_schema": capability.params_schema,
                    "returns_schema": capability.returns_schema,
                }
        return None

    def _load_capabilities(self) -> List[Capability]:
        """Load capabilities from built-ins and future registries."""

        # For now only built-ins exist. Hook for MCP registry integration later.
        return list(self._builtin_capabilities)
