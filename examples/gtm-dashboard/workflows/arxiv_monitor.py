"""arXiv Monitor Workflow

Replaces the n8n "arXiv Paper Ingestion" cron job.
Searches arXiv for recent papers in specified categories and keywords,
transforms them into the standard signal format, and ingests into
the Tapcraft signal pipeline.
"""

from datetime import timedelta

from temporalio import workflow

DEFAULT_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]
DEFAULT_KEYWORDS = ["agent", "LLM", "automation"]


@workflow.defn
class ArxivMonitorWorkflow:
    """Fetch arXiv papers and ingest as signals."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        categories = config.get("categories", DEFAULT_CATEGORIES)
        keywords = config.get("keywords", DEFAULT_KEYWORDS)
        max_results = config.get("max_results", 30)
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )

        # Search arXiv
        result = await workflow.execute_activity(
            "arxiv.search",
            {
                "categories": categories,
                "keywords": keywords,
                "max_results": max_results,
            },
            start_to_close_timeout=timedelta(minutes=3),
        )
        papers = result.get("papers", [])

        if not papers:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_ingested": 0,
            }

        # Transform papers into signal format
        transform_code = """
signals = []
for paper in input_data:
    signals.append({
        "source": "arxiv",
        "source_id": f"arxiv_{paper['url']}",
        "title": paper["title"],
        "url": paper["url"],
        "content": paper["abstract"],
        "metadata": {
            "authors": paper["authors"],
            "published": paper["published"],
        },
    })
result = signals
"""
        transform_result = await workflow.execute_activity(
            "data.transform",
            {"input_data": papers, "code": transform_code},
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
            "total_fetched": len(papers),
            "total_ingested": ingest_result.get("ingested", len(signals)),
        }
