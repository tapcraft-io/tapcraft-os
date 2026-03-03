"""Hacker News activity - search stories via Algolia HN API."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

import httpx
from temporalio import activity

LOGGER = logging.getLogger(__name__)

ALGOLIA_HN_API = "https://hn.algolia.com/api/v1/search_by_date"


@activity.defn(name="hackernews.search")
async def search(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search Hacker News stories via the Algolia HN API.

    Args:
        config: Dict containing:
            - query: Search query string
            - tags: HN tag filter (default "story")
            - hours_back: How many hours back to search (default 24)

    Returns:
        Dict with stories list, each containing title, url, points,
        author, created_at, and num_comments.
    """
    query = config.get("query", "")
    tags = config.get("tags", "story")
    hours_back = config.get("hours_back", 24)

    # Calculate the timestamp for hours_back
    now = int(time.time())
    created_after = now - (hours_back * 3600)
    numeric_filters = f"created_at_i>{created_after}"

    LOGGER.info(
        f"Searching HN for '{query}' (tags={tags}, last {hours_back}h)"
    )

    try:
        params = {
            "query": query,
            "tags": tags,
            "numericFilters": numeric_filters,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                ALGOLIA_HN_API,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()

        data = response.json()
        hits = data.get("hits", [])

        stories = []
        for hit in hits:
            stories.append({
                "title": hit.get("title", ""),
                "url": hit.get("url", ""),
                "points": hit.get("points", 0),
                "author": hit.get("author", ""),
                "created_at": hit.get("created_at", ""),
                "num_comments": hit.get("num_comments", 0),
            })

        LOGGER.info(f"Found {len(stories)} HN stories for '{query}'")
        return {"stories": stories}

    except httpx.HTTPStatusError as e:
        LOGGER.error(f"HTTP error searching HN: {e.response.status_code}")
        return {"stories": [], "error": f"HTTP {e.response.status_code}: {str(e)}"}
    except Exception as e:
        LOGGER.error(f"Error searching HN: {e}")
        return {"stories": [], "error": str(e)}
