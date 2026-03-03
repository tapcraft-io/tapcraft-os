"""Reddit Monitor Workflow

Replaces the n8n "Reddit Signal Ingestion" cron job.
Fetches recent posts from a configurable list of subreddits,
transforms them into the standard signal format, and ingests
them into the Tapcraft signal pipeline.
"""

from datetime import timedelta

from temporalio import workflow

DEFAULT_SUBREDDITS = [
    "machinelearning",
    "artificial",
    "LocalLLaMA",
    "programming",
    "technology",
    "startups",
    "SaaS",
]


@workflow.defn
class RedditMonitorWorkflow:
    """Fetch Reddit posts from multiple subreddits and ingest as signals."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        subreddits = config.get("subreddits", DEFAULT_SUBREDDITS)
        limit = config.get("limit", 25)
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )

        all_posts: list[dict] = []
        fetch_results: dict[str, int] = {}

        # Fetch posts from each subreddit
        for subreddit in subreddits:
            result = await workflow.execute_activity(
                "reddit.fetch_posts",
                {"subreddit": subreddit, "limit": limit},
                start_to_close_timeout=timedelta(minutes=2),
            )
            posts = result.get("posts", [])
            # Tag each post with its subreddit for the transform step
            for post in posts:
                post["_subreddit"] = subreddit
            all_posts.extend(posts)
            fetch_results[subreddit] = len(posts)

        if not all_posts:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_ingested": 0,
                "by_subreddit": fetch_results,
            }

        # Transform posts into signal format
        transform_code = """
signals = []
for post in input_data:
    subreddit = post.get("_subreddit", "unknown")
    signals.append({
        "source": "reddit",
        "source_id": f"reddit_{post['url']}",
        "title": post["title"],
        "url": post["url"],
        "content": post.get("selftext", ""),
        "metadata": {
            "score": post["score"],
            "subreddit": subreddit,
            "author": post["author"],
            "num_comments": post["num_comments"],
        },
    })
result = signals
"""
        transform_result = await workflow.execute_activity(
            "data.transform",
            {"input_data": all_posts, "code": transform_code},
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
            "total_fetched": len(all_posts),
            "total_ingested": ingest_result.get("ingested", len(signals)),
            "by_subreddit": fetch_results,
        }
