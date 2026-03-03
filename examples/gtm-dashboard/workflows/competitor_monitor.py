"""Competitor Monitor Workflow

Replaces the n8n "Competitor Monitoring" cron job.
Triggers a competitor scanning process via the GTM API on a schedule.
The GTM API endpoint crawls tracked competitor sources and updates
the competitive intelligence database.
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class CompetitorMonitorWorkflow:
    """Trigger competitor monitoring scan on a schedule."""

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
                "url": f"{api_base_url}/api/competitors/scan",
                "headers": {"Content-Type": "application/json"},
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
