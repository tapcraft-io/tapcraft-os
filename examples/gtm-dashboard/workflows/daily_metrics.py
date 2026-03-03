"""Daily Metrics Workflow

Replaces the n8n "Daily Metrics Pull" cron job.
Triggers the GTM API to pull and aggregate daily metrics from
connected data sources (analytics, CRM, ad platforms, etc.).
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class DailyMetricsWorkflow:
    """Pull daily metrics on a schedule."""

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
                "url": f"{api_base_url}/api/metrics/pull",
                "headers": {"Content-Type": "application/json"},
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
