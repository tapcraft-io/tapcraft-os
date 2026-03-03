"""Signal Intelligence Workflow

Replaces the n8n "Signal Intelligence Recompute" cron job.
Triggers the GTM API to recompute signal intelligence scores
and rankings based on the latest ingested data from all sources.
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class SignalIntelligenceWorkflow:
    """Recompute signal intelligence on a schedule."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )

        result = await workflow.execute_activity(
            "net.http.request",
            {
                "method": "POST",
                "url": f"{api_base_url}/api/signals/intelligence/recompute",
                "headers": {"Content-Type": "application/json"},
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
