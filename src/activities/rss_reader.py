"""RSS / Atom feed reader activity for Temporal workflows."""

from __future__ import annotations

import logging
from typing import Any, Dict

from temporalio import activity

LOGGER = logging.getLogger(__name__)

_DEFAULT_MAX_ITEMS = 20


@activity.defn(name="feed.rss.read")
async def rss_read(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch and parse an RSS or Atom feed.

    Args:
        config: Dict containing:
            - url: The feed URL to fetch.
            - max_items: Maximum number of items to return (default 20).

    Returns:
        dict with ``items`` (list of entry dicts) and ``count``.
    """
    import feedparser  # type: ignore[import-untyped]

    url = config.get("url", "")
    max_items = config.get("max_items", _DEFAULT_MAX_ITEMS)

    if not url:
        return {"items": [], "count": 0, "error": "No URL provided"}

    LOGGER.info("feed.rss.read: fetching feed from %s", url)

    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        LOGGER.error("feed.rss.read: failed to parse feed: %s", exc)
        return {"items": [], "count": 0, "error": str(exc)}

    if feed.bozo and not feed.entries:
        error_msg = str(feed.bozo_exception) if feed.bozo_exception else "Unknown parse error"
        LOGGER.error("feed.rss.read: feed error: %s", error_msg)
        return {"items": [], "count": 0, "error": error_msg}

    items = []
    for entry in feed.entries[:max_items]:
        items.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "author": entry.get("author", ""),
            }
        )

    LOGGER.info("feed.rss.read: parsed %d items from %s", len(items), url)
    return {"items": items, "count": len(items)}
