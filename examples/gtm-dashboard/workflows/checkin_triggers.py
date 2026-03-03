"""Check-In Triggers Workflow

Replaces the n8n "Morning Brief" and "Evening Wrap" cron jobs.
Triggers the GTM API to run check-in routines. Supports running
the morning brief, evening wrap, or both sequentially.

Config options:
    type: "morning" | "evening" | "both" (default: "both")
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class CheckInTriggersWorkflow:
    """Trigger check-in routines (morning brief and/or evening wrap) on a schedule."""

    @workflow.run
    async def run(self, config: dict) -> dict:
        api_base_url = config.get(
            "api_base_url",
            "http://localhost:8000",
        )
        checkin_type = config.get("type", "both")

        results = {}

        if checkin_type in ("morning", "both"):
            morning_result = await workflow.execute_activity(
                "net.http.request",
                {
                    "method": "POST",
                    "url": f"{api_base_url}/api/checkins/morning-brief",
                    "headers": {"Content-Type": "application/json"},
                },
                start_to_close_timeout=timedelta(minutes=5),
            )
            results["morning_brief"] = morning_result

        if checkin_type in ("evening", "both"):
            evening_result = await workflow.execute_activity(
                "net.http.request",
                {
                    "method": "POST",
                    "url": f"{api_base_url}/api/checkins/evening-wrap",
                    "headers": {"Content-Type": "application/json"},
                },
                start_to_close_timeout=timedelta(minutes=5),
            )
            results["evening_wrap"] = evening_result

        return results
