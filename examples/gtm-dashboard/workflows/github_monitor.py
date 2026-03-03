"""GitHub Monitor Workflow

Replaces the n8n "GitHub Activity Ingestion" cron job.
Fetches recent events from specified GitHub repositories,
transforms them into the standard signal format, and ingests
into the Tapcraft signal pipeline.
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class GitHubMonitorWorkflow:
    """Fetch GitHub repo events and ingest as signals."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        repos = config.get("repos", [])
        per_page = config.get("per_page", 30)
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )

        if not repos:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_ingested": 0,
                "by_repo": {},
                "message": "No repos configured. Provide a 'repos' list with {owner, repo} entries.",
            }

        all_events: list[dict] = []
        fetch_results: dict[str, int] = {}

        # Fetch events from each repository
        for repo_entry in repos:
            owner = repo_entry["owner"]
            repo = repo_entry["repo"]
            repo_name = f"{owner}/{repo}"

            result = await workflow.execute_activity(
                "github.fetch_events",
                {"owner": owner, "repo": repo, "per_page": per_page},
                start_to_close_timeout=timedelta(minutes=2),
            )
            events = result.get("events", [])
            # Tag each event with its repo name for the transform step
            for event in events:
                event["_repo_name"] = repo_name
            all_events.extend(events)
            fetch_results[repo_name] = len(events)

        if not all_events:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_ingested": 0,
                "by_repo": fetch_results,
            }

        # Transform events into signal format
        transform_code = """
signals = []
for event in input_data:
    repo_name = event.get("_repo_name", "unknown")
    signals.append({
        "source": "github",
        "source_id": f"gh_{event['type']}_{event['created_at']}",
        "title": f"{event['type']} on {repo_name}",
        "url": "",
        "content": str(event.get("payload_summary", "")),
        "metadata": {
            "event_type": event["type"],
            "actor": event["actor"],
            "repo": repo_name,
        },
    })
result = signals
"""
        transform_result = await workflow.execute_activity(
            "data.transform",
            {"input_data": all_events, "code": transform_code},
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
            "total_fetched": len(all_events),
            "total_ingested": ingest_result.get("ingested", len(signals)),
            "by_repo": fetch_results,
        }
