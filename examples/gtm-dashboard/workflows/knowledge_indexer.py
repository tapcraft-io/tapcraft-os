"""Knowledge Indexer Workflow

Replaces the n8n "Knowledge Base Indexer" cron job.
Triggers the GTM API to index the latest signals into the RAG
knowledge base so they are available for semantic search and
AI-powered analysis.
"""

from datetime import timedelta

from temporalio import workflow

@workflow.defn
class KnowledgeIndexerWorkflow:
    """Index signals into knowledge base on a schedule."""

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
                "url": f"{api_base_url}/api/rag/index/signals",
                "headers": {"Content-Type": "application/json"},
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
