"""Simple API key authentication for Tapcraft OS.

Single-tenant, self-hosted. One API key gates all access.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

LOGGER = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)

_DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
_KEY_FILE = _DATA_DIR / "api_key"


def _load_or_generate_key() -> str:
    """Return the API key from env, file, or generate a new one."""
    # 1. Environment variable takes precedence
    env_key = os.getenv("TAPCRAFT_API_KEY", "").strip()
    if env_key:
        return env_key

    # 2. Read from persisted file
    if _KEY_FILE.exists():
        stored = _KEY_FILE.read_text().strip()
        if stored:
            return stored

    # 3. Generate and persist
    new_key = f"tc_{secrets.token_urlsafe(32)}"
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _KEY_FILE.write_text(new_key + "\n")
    LOGGER.info(
        "\n"
        "============================================================\n"
        "  TAPCRAFT API KEY (auto-generated, save this!):\n"
        "  %s\n"
        "============================================================",
        new_key,
    )
    return new_key


# Resolve once at import time
_API_KEY: str = _load_or_generate_key()


def get_api_key() -> str:
    """Return the active API key (for use in tests or MCP)."""
    return _API_KEY


async def require_api_key(
    header_key: str | None = Security(API_KEY_HEADER),
    query_key: str | None = Security(API_KEY_QUERY),
) -> str:
    """FastAPI dependency that enforces API key auth.

    Accepts the key via ``X-API-Key`` header or ``?api_key=`` query param.
    """
    provided = header_key or query_key
    if not provided:
        raise HTTPException(status_code=401, detail="Missing API key")
    if not secrets.compare_digest(provided, _API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return provided


# Auth validation endpoint helper — called by the UI to check if a key is valid
async def validate_key(request: Request) -> dict:
    """Lightweight endpoint the UI calls to test a key before storing it."""
    header_key = request.headers.get("X-API-Key")
    query_key = request.query_params.get("api_key")
    provided = header_key or query_key
    if provided and secrets.compare_digest(provided, _API_KEY):
        return {"valid": True}
    raise HTTPException(status_code=401, detail="Invalid API key")
