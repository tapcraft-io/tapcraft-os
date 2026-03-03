"""Apify Social Monitor Workflow

Replaces the n8n "Social Media Scraping via Apify" cron job.
Runs one or more Apify actors (e.g. Twitter scraper, LinkedIn scraper),
polls for completion, collects results, transforms them into the
standard signal format, and ingests into the Tapcraft signal pipeline.
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class ApifySocialMonitorWorkflow:
    """Run Apify actors, poll for results, and ingest as signals."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        actors = config.get("actors", [])
        poll_interval_seconds = config.get("poll_interval_seconds", 30)
        max_poll_attempts = config.get("max_poll_attempts", 20)
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )

        if not actors:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_ingested": 0,
                "by_actor": {},
                "message": "No actors configured. Provide an 'actors' list with {actor_id, input_data, label} entries.",
            }

        all_results: list[dict] = []
        actor_results: dict[str, int] = {}

        # Run each actor and poll for results
        for actor_entry in actors:
            actor_id = actor_entry["actor_id"]
            input_data = actor_entry.get("input_data", {})
            label = actor_entry.get("label", actor_id)

            # Start the actor run
            run_result = await workflow.execute_activity(
                "apify.run_actor",
                {"actor_id": actor_id, "input_data": input_data},
                start_to_close_timeout=timedelta(minutes=5),
            )
            run_id = run_result.get("run_id", "")

            if not run_id:
                actor_results[label] = 0
                continue

            # Poll for results until completion or max attempts
            items: list[dict] = []
            for attempt in range(max_poll_attempts):
                results_response = await workflow.execute_activity(
                    "apify.get_results",
                    {"run_id": run_id},
                    start_to_close_timeout=timedelta(minutes=2),
                )

                status = results_response.get("status", "")
                if status == "SUCCEEDED":
                    items = results_response.get("items", [])
                    break
                elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    # Actor run failed; move on
                    break

                # Still running; wait before polling again
                if attempt < max_poll_attempts - 1:
                    await workflow.sleep(poll_interval_seconds)

            # Tag each item with its actor label for the transform step
            for item in items:
                item["_actor_label"] = label
            all_results.extend(items)
            actor_results[label] = len(items)

        if not all_results:
            return {
                "status": "complete",
                "total_fetched": 0,
                "total_ingested": 0,
                "by_actor": actor_results,
            }

        # Transform results into signal format
        transform_code = """
signals = []
for item in input_data:
    label = item.get("_actor_label", "apify")
    # Build a useful title from available fields
    title = item.get("title") or item.get("text", "")[:120] or f"Apify result from {label}"
    url = item.get("url") or item.get("link", "")
    content = item.get("text") or item.get("description") or item.get("body", "")
    item_id = item.get("id") or item.get("url") or str(hash(str(item)))

    signals.append({
        "source": f"apify_{label}",
        "source_id": f"apify_{label}_{item_id}",
        "title": title,
        "url": url,
        "content": content,
        "metadata": {
            "actor_label": label,
            "raw_fields": {k: v for k, v in item.items() if not k.startswith("_")},
        },
    })
result = signals
"""
        transform_result = await workflow.execute_activity(
            "data.transform",
            {"input_data": all_results, "code": transform_code},
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
            "total_fetched": len(all_results),
            "total_ingested": ingest_result.get("ingested", len(signals)),
            "by_actor": actor_results,
        }
