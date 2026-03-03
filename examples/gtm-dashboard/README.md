# GTM Dashboard — Tapcraft Example Project

This is an example Tapcraft project containing domain-specific activities and workflows for a Go-To-Market intelligence dashboard.

## Structure

```
activities/         # Temporal activity functions (@activity.defn)
  reddit.py         # Fetch hot posts from subreddits
  hackernews.py     # Search HN stories via Algolia API
  arxiv.py          # Search arXiv papers
  github_events.py  # Fetch GitHub repository events
  apify.py          # Run Apify actors and retrieve results
  signals.py        # Ingest signals to a GTM API endpoint

workflows/          # Temporal workflow classes (@workflow.defn)
  reddit_monitor.py
  hackernews_monitor.py
  arxiv_monitor.py
  news_rss_monitor.py
  github_monitor.py
  apify_social.py
  competitor_monitor.py
  daily_metrics.py
  seo_report.py
  signal_intelligence.py
  notion_sync.py
  knowledge_indexer.py
  landscape_snapshot.py
  checkin_triggers.py
```

## Usage

1. Push this directory to a git repo (or use it as a subdirectory of one).
2. In Tapcraft, create a workspace and set its `repo_url` to your git repo.
3. Call `POST /api/workspaces/{id}/sync` to clone the repo.
4. The worker will automatically discover activities and workflows from the cloned repo.

## Required Secrets

Some activities require secrets configured in Tapcraft (Settings > Secrets):

| Secret Name      | Used By              | Description                     |
|------------------|----------------------|---------------------------------|
| `github_token`   | `github_events.py`   | GitHub Personal Access Token    |
| `apify_api_key`  | `apify.py`           | Apify API token                 |

## Environment Variables

| Variable                         | Default               | Description                          |
|----------------------------------|-----------------------|--------------------------------------|
| `TAPCRAFT_WF_GTM_API_BASE`      | `http://localhost:8000` | Base URL for the GTM API           |
| `TAPCRAFT_WF_DEFAULT_USER_AGENT` | `TapcraftBot/1.0`    | User-Agent for HTTP requests        |
