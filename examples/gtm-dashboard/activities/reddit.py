"""Reddit activity - fetch posts from subreddits."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import httpx
from temporalio import activity

LOGGER = logging.getLogger(__name__)


@activity.defn(name="reddit.fetch_posts")
async def fetch_posts(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch hot posts from a subreddit.

    Args:
        config: Dict containing:
            - subreddit: The subreddit name (without /r/ prefix)
            - limit: Max number of posts to return (default 25)

    Returns:
        Dict with posts list, each containing title, url, score, author,
        created, selftext, and num_comments.
    """
    subreddit = config.get("subreddit", "")
    limit = config.get("limit", 25)

    if not subreddit:
        return {"posts": [], "error": "No subreddit specified"}

    user_agent = os.environ.get("TAPCRAFT_WF_DEFAULT_USER_AGENT", "TapcraftBot/1.0")
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

    LOGGER.info(f"Fetching up to {limit} posts from r/{subreddit}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": user_agent},
                timeout=30.0,
                follow_redirects=True,
            )
            response.raise_for_status()

        data = response.json()
        children = data.get("data", {}).get("children", [])

        posts = []
        for child in children:
            post_data = child.get("data", {})
            posts.append({
                "title": post_data.get("title", ""),
                "url": post_data.get("url", ""),
                "score": post_data.get("score", 0),
                "author": post_data.get("author", ""),
                "created": post_data.get("created_utc", 0),
                "selftext": post_data.get("selftext", ""),
                "num_comments": post_data.get("num_comments", 0),
            })

        LOGGER.info(f"Fetched {len(posts)} posts from r/{subreddit}")
        return {"posts": posts}

    except httpx.HTTPStatusError as e:
        LOGGER.error(f"HTTP error fetching r/{subreddit}: {e.response.status_code}")
        return {"posts": [], "error": f"HTTP {e.response.status_code}: {str(e)}"}
    except Exception as e:
        LOGGER.error(f"Error fetching r/{subreddit}: {e}")
        return {"posts": [], "error": str(e)}
