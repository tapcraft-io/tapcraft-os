"""GitHub Events activity - fetch repository events via the GitHub REST API."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from temporalio import activity

from src.services.secrets import get_secret

LOGGER = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


@activity.defn(name="github.fetch_events")
async def fetch_events(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch recent events for a GitHub repository.

    Args:
        config: Dict containing:
            - owner: Repository owner (user or org)
            - repo: Repository name
            - per_page: Number of events to fetch (default 30)

    Returns:
        Dict with events list, each containing type, actor, repo,
        payload_summary, and created_at.
    """
    owner = config.get("owner", "")
    repo = config.get("repo", "")
    per_page = config.get("per_page", 30)

    if not owner or not repo:
        return {"events": [], "error": "Both 'owner' and 'repo' are required"}

    url = f"{GITHUB_API}/repos/{owner}/{repo}/events"

    # Try to get GitHub token for authenticated requests (higher rate limit)
    token: Optional[str] = None
    try:
        token = await get_secret("github_token")
    except KeyError:
        LOGGER.info(
            "No github_token secret configured; proceeding without auth "
            "(rate limit: 60 req/hour)"
        )

    headers: Dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    LOGGER.info(f"Fetching up to {per_page} events for {owner}/{repo}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={"per_page": per_page},
                timeout=30.0,
            )
            response.raise_for_status()

        raw_events = response.json()

        events = []
        for event in raw_events:
            events.append({
                "type": event.get("type", ""),
                "actor": event.get("actor", {}).get("login", ""),
                "repo": event.get("repo", {}).get("name", ""),
                "payload_summary": _summarize_payload(
                    event.get("type", ""), event.get("payload", {})
                ),
                "created_at": event.get("created_at", ""),
            })

        LOGGER.info(f"Fetched {len(events)} events for {owner}/{repo}")
        return {"events": events}

    except httpx.HTTPStatusError as e:
        LOGGER.error(
            f"HTTP error fetching events for {owner}/{repo}: "
            f"{e.response.status_code}"
        )
        return {
            "events": [],
            "error": f"HTTP {e.response.status_code}: {str(e)}",
        }
    except Exception as e:
        LOGGER.error(f"Error fetching events for {owner}/{repo}: {e}")
        return {"events": [], "error": str(e)}


def _summarize_payload(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a compact summary of the event payload.

    Only keeps the most relevant fields to avoid huge payloads.
    """
    summary: Dict[str, Any] = {"type": event_type}

    if event_type == "PushEvent":
        summary["size"] = payload.get("size", 0)
        summary["ref"] = payload.get("ref", "")
        commits = payload.get("commits", [])
        summary["commits"] = [
            {"sha": c.get("sha", "")[:7], "message": c.get("message", "")[:120]}
            for c in commits[:5]  # Keep at most 5 commit summaries
        ]

    elif event_type == "PullRequestEvent":
        summary["action"] = payload.get("action", "")
        pr = payload.get("pull_request", {})
        summary["title"] = pr.get("title", "")
        summary["number"] = pr.get("number")
        summary["state"] = pr.get("state", "")

    elif event_type == "IssuesEvent":
        summary["action"] = payload.get("action", "")
        issue = payload.get("issue", {})
        summary["title"] = issue.get("title", "")
        summary["number"] = issue.get("number")

    elif event_type == "IssueCommentEvent":
        summary["action"] = payload.get("action", "")
        comment = payload.get("comment", {})
        summary["body_preview"] = (comment.get("body", ""))[:200]

    elif event_type == "CreateEvent":
        summary["ref_type"] = payload.get("ref_type", "")
        summary["ref"] = payload.get("ref", "")

    elif event_type == "DeleteEvent":
        summary["ref_type"] = payload.get("ref_type", "")
        summary["ref"] = payload.get("ref", "")

    elif event_type == "WatchEvent":
        summary["action"] = payload.get("action", "")

    elif event_type == "ForkEvent":
        forkee = payload.get("forkee", {})
        summary["fork_full_name"] = forkee.get("full_name", "")

    elif event_type == "ReleaseEvent":
        summary["action"] = payload.get("action", "")
        release = payload.get("release", {})
        summary["tag_name"] = release.get("tag_name", "")
        summary["name"] = release.get("name", "")

    else:
        # For unknown event types, include the action if present
        action = payload.get("action")
        if action:
            summary["action"] = action

    return summary
