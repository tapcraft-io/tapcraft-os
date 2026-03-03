"""Parallel HTTP request activity for Temporal workflows."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from temporalio import activity

LOGGER = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0  # seconds per request


async def _execute_request(
    request: Dict[str, Any],
    timeout: float,
) -> Dict[str, Any]:
    """Execute a single HTTP request and return a structured result."""
    import httpx

    label = request.get("label", request.get("url", "unknown"))
    method = request.get("method", "GET").upper()
    url = request.get("url", "")
    headers = request.get("headers") or {}
    body = request.get("body")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body if isinstance(body, (str, bytes)) else None,
                json=body if isinstance(body, (dict, list)) else None,
            )
            return {
                "label": label,
                "status_code": response.status_code,
                "body": response.text,
                "headers": dict(response.headers),
                "error": None,
            }
    except Exception as exc:
        LOGGER.error("net.http.parallel: request to %s failed: %s", url, exc)
        return {
            "label": label,
            "status_code": None,
            "body": None,
            "headers": None,
            "error": str(exc),
        }


@activity.defn(name="net.http.parallel")
async def http_parallel(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run multiple HTTP requests in parallel using asyncio.gather.

    Args:
        config: Dict containing:
            - requests: List of request dicts, each with:
                - method: HTTP method (default GET)
                - url: Target URL
                - headers: Optional dict of headers
                - body: Optional request body (string, bytes, dict, or list)
                - label: Optional human-readable label for the request
            - timeout: Optional per-request timeout in seconds (default 30)

    Returns:
        dict with ``results`` (list of result dicts) and ``count``.
    """
    requests: List[Dict[str, Any]] = config.get("requests", [])
    timeout: float = config.get("timeout", _DEFAULT_TIMEOUT)

    if not requests:
        return {"results": [], "count": 0}

    LOGGER.info("net.http.parallel: dispatching %d requests", len(requests))

    tasks = [_execute_request(req, timeout) for req in requests]
    results = await asyncio.gather(*tasks)

    LOGGER.info("net.http.parallel: completed %d requests", len(results))
    return {"results": list(results), "count": len(results)}
