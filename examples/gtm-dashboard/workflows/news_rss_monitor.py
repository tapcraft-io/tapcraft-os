"""News RSS Monitor Workflow

Replaces the n8n "Tech News RSS Ingestion" cron job.
Reads multiple RSS feeds from major tech news outlets,
deduplicates items by link, transforms them into the standard
signal format, and ingests into the Tapcraft signal pipeline.
"""

from datetime import timedelta

from temporalio import workflow

DEFAULT_FEEDS = [
    {
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "label": "TechCrunch",
    },
    {
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "label": "The Verge AI",
    },
    {
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "label": "Ars Technica",
    },
    {
        "url": "https://venturebeat.com/category/ai/feed/",
        "label": "VentureBeat AI",
    },
]


@workflow.defn
class NewsRssMonitorWorkflow:
    """Read tech news RSS feeds and ingest as signals."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        feeds = config.get("feeds", DEFAULT_FEEDS)
        max_items = config.get("max_items", 20)
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )

        all_items: list[dict] = []
        fetch_results: dict[str, int] = {}

        # Read items from each feed
        for feed in feeds:
            feed_url = feed["url"]
            feed_label = feed["label"]

            result = await workflow.execute_activity(
                "feed.rss.read",
                {"url": feed_url, "max_items": max_items},
                start_to_close_timeout=timedelta(minutes=2),
            )
            items = result.get("items", [])
            # Tag each item with its feed label for the transform step
            for item in items:
                item["_feed_label"] = feed_label
            all_items.extend(items)
            fetch_results[feed_label] = len(items)

        if not all_items:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_after_dedup": 0,
                "total_ingested": 0,
                "by_feed": fetch_results,
            }

        # Deduplicate by link
        dedup_result = await workflow.execute_activity(
            "data.dedup",
            {"items": all_items, "key_field": "link"},
            start_to_close_timeout=timedelta(minutes=1),
        )
        unique_items = dedup_result.get("items", all_items)

        # Transform items into signal format
        transform_code = """
signals = []
for item in input_data:
    feed_label = item.get("_feed_label", "unknown")
    signals.append({
        "source": f"rss_{feed_label}",
        "source_id": f"rss_{item['link']}",
        "title": item["title"],
        "url": item["link"],
        "content": item.get("summary", ""),
        "metadata": {
            "feed": feed_label,
            "published": item.get("published", ""),
            "author": item.get("author", ""),
        },
    })
result = signals
"""
        transform_result = await workflow.execute_activity(
            "data.transform",
            {"input_data": unique_items, "code": transform_code},
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
            "total_fetched": len(all_items),
            "total_after_dedup": len(unique_items),
            "total_ingested": ingest_result.get("ingested", len(signals)),
            "by_feed": fetch_results,
        }
