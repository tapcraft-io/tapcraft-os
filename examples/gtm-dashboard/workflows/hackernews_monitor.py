"""Hacker News Monitor Workflow

Replaces the n8n "HN Signal Ingestion" cron job.
Searches Hacker News for stories matching configurable queries,
deduplicates them by URL, transforms into the standard signal format,
and ingests into the Tapcraft signal pipeline.
"""

from datetime import timedelta

from temporalio import workflow

DEFAULT_QUERIES = [
    "AI agent",
    "LLM",
    "automation",
    "developer tools",
    "SaaS",
]


@workflow.defn
class HackerNewsMonitorWorkflow:
    """Search Hacker News for stories and ingest as signals."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        queries = config.get("queries", DEFAULT_QUERIES)
        hours_back = config.get("hours_back", 24)
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )

        all_stories: list[dict] = []
        fetch_results: dict[str, int] = {}

        # Search for each query
        for query in queries:
            result = await workflow.execute_activity(
                "hackernews.search",
                {"query": query, "tags": "story", "hours_back": hours_back},
                start_to_close_timeout=timedelta(minutes=2),
            )
            stories = result.get("hits", [])
            all_stories.extend(stories)
            fetch_results[query] = len(stories)

        if not all_stories:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_after_dedup": 0,
                "total_ingested": 0,
                "by_query": fetch_results,
            }

        # Deduplicate by URL
        dedup_result = await workflow.execute_activity(
            "data.dedup",
            {"items": all_stories, "key_field": "url"},
            start_to_close_timeout=timedelta(minutes=1),
        )
        unique_stories = dedup_result.get("items", all_stories)

        # Transform stories into signal format
        transform_code = """
signals = []
for story in input_data:
    signals.append({
        "source": "hackernews",
        "source_id": f"hn_{story['url']}",
        "title": story["title"],
        "url": story.get("url", ""),
        "content": "",
        "metadata": {
            "points": story["points"],
            "author": story["author"],
            "num_comments": story["num_comments"],
        },
    })
result = signals
"""
        transform_result = await workflow.execute_activity(
            "data.transform",
            {"input_data": unique_stories, "code": transform_code},
            start_to_close_timeout=timedelta(minutes=2),
        )
        signals = transform_result.get("result", [])

        # Ingest signals
        ingest_result = await workflow.execute_activity(
            "signals.ingest",
            {"signals": signals, "api_base_url": api_base_url},
            start_to_close_timeout=timedelta(minutes=3),
        )

        return {
            "status": "complete",
            "total_fetched": len(all_stories),
            "total_after_dedup": len(unique_stories),
            "total_ingested": ingest_result.get("ingested", len(signals)),
            "by_query": fetch_results,
        }
