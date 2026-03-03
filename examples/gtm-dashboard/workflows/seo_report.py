"""SEO Weekly Report Workflow

Replaces the n8n "SEO Weekly Report" cron job.
Triggers the GTM API to generate a weekly SEO performance report
covering rankings, organic traffic, backlinks, and keyword movements.
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class SeoWeeklyReportWorkflow:
    """Generate SEO weekly report on a schedule."""

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
                "url": f"{api_base_url}/api/seo/report",
                "headers": {"Content-Type": "application/json"},
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
