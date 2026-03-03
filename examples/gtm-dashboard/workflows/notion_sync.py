"""Notion Sync Workflow

Replaces the n8n "Notion Sync All" cron job.
Triggers the GTM API to synchronize all connected Notion databases,
pulling updates and pushing any pending changes.
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class NotionSyncWorkflow:
    """Sync all Notion data on a schedule."""

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
                "url": f"{api_base_url}/api/notion/sync/all",
                "headers": {"Content-Type": "application/json"},
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
