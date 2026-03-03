"""Signals activity - ingest signals to a GTM API endpoint."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx
from temporalio import activity

LOGGER = logging.getLogger(__name__)


@activity.defn(name="signals.ingest")
async def ingest(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest signals by POSTing them to a GTM API endpoint.

    Args:
        config: Dict containing:
            - signals: List of signal dicts to ingest
            - api_base_url: Base URL for the GTM API (optional, falls back
              to TAPCRAFT_WF_GTM_API_BASE env var)

    Returns:
        Dict with ingested_count and errors list.
    """
    signals: List[Dict[str, Any]] = config.get("signals", [])
    api_base_url = config.get(
        "api_base_url",
        os.environ.get("TAPCRAFT_WF_GTM_API_BASE", ""),
    )

    if not signals:
        return {"ingested_count": 0, "errors": []}

    if not api_base_url:
        return {
            "ingested_count": 0,
            "errors": [
                "No api_base_url provided and TAPCRAFT_WF_GTM_API_BASE "
                "environment variable is not set"
            ],
        }

    # Strip trailing slash for clean URL construction
    api_base_url = api_base_url.rstrip("/")
    ingest_url = f"{api_base_url}/api/signals/ingest"

    LOGGER.info(f"Ingesting {len(signals)} signals to {ingest_url}")

    ingested_count = 0
    errors: List[str] = []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ingest_url,
                json=signals,
                timeout=60.0,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            ingested_count = len(signals)
            LOGGER.info(f"Successfully ingested {ingested_count} signals")

    except httpx.HTTPStatusError as e:
        error_msg = (
            f"HTTP {e.response.status_code} from {ingest_url}: "
            f"{e.response.text[:500]}"
        )
        LOGGER.error(f"Error ingesting signals: {error_msg}")
        errors.append(error_msg)
    except httpx.ConnectError as e:
        error_msg = f"Connection error to {ingest_url}: {str(e)}"
        LOGGER.error(error_msg)
        errors.append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error ingesting signals: {str(e)}"
        LOGGER.error(error_msg)
        errors.append(error_msg)

    return {"ingested_count": ingested_count, "errors": errors}
