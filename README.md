# Tapcraft OS

Tapcraft OS is a self-hosted workflow automation platform built on [Temporal](https://temporal.io).
Define reusable activities, compose them into durable workflows with a visual graph editor,
schedule runs, and monitor execution — all from a clean web UI.

## Features

- **Visual workflow editor** – build directed acyclic graphs of activities and connect them with edges
- **Durable execution** – all workflows run on Temporal, giving you retries, timeouts, and history out of the box
- **Agent-driven via MCP** – connect Claude Code or any MCP-compatible coding agent to deploy and run workflows without touching the UI
- **Git-backed workspaces** – point a workspace at a git repo; Tapcraft clones it and auto-discovers your activities and workflows
- **Schedules** – trigger workflows on a cron schedule with timezone support
- **Secrets management** – store encrypted credentials used by activities at runtime

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Node.js](https://nodejs.org/) 18+ (for the UI dev server)

### Running the stack

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

Start Temporal, the API service, and the worker:

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8001 |
| Temporal UI | http://localhost:8082 |

### UI

The `ui/` directory is a Vite + React + Tailwind application. Install dependencies and start
the development server:

```bash
cd ui
npm install
npm run dev
```

Open http://localhost:5180. The dev server proxies API calls to `http://localhost:8001`.

## How It Works

Tapcraft is designed to be driven by a coding agent (Claude Code, GitHub Copilot, etc.) via the
[Model Context Protocol](https://modelcontextprotocol.io). The typical flow is:

1. **Point your agent at the MCP server** — the server exposes tools for deploying workflows,
   running them, managing secrets and schedules, and syncing code from a git repo.
2. **Write workflow code in your own git repo** — activities go in `activities/`, workflows in
   `workflows/`. Tapcraft clones the repo into its workspace and discovers them automatically.
3. **Trigger runs from the UI or via the agent** — Tapcraft executes everything on Temporal,
   giving you durable retries, timeouts, and full execution history.

### Connecting Claude Code

Run the MCP server locally (with the same environment the Docker stack uses):

```bash
poetry run tapcraft-mcp
```

Then add it to your Claude Code MCP config (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tapcraft": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/tapcraft-os",
      "env": {
        "DATABASE_URL": "sqlite+aiosqlite:///./data/tapcraft.db",
        "TEMPORAL_ADDRESS": "localhost:7233"
      }
    }
  }
}
```

The MCP server exposes tools for listing/deploying/running workflows, managing activities,
secrets, and schedules, as well as resources at `tapcraft://docs/*` that describe how to
write Temporal workflows and activities for Tapcraft.

### Git repo sync

Each workspace can be connected to a git repo containing your workflow code. Configure the
workspace's `repo_url` and `repo_branch` via the UI or the `tapcraft_sync_repo` MCP tool.
If the repo requires authentication, store a personal access token as a Tapcraft secret and
reference it in `repo_auth_secret`. Tapcraft will shallow-clone (or pull) the repo and
auto-discover `@activity.defn` functions and `@workflow.defn` classes from the
`activities/` and `workflows/` directories.

## Project Layout

```
src/
  api/         # FastAPI application and route handlers
  activities/  # Built-in Temporal activity definitions
  config/      # Runtime configuration helpers
  db/          # SQLAlchemy models and database setup
  mcp/         # MCP server integration
  models/      # Shared Pydantic models
  services/    # Business logic and CRUD layer
  worker/      # Temporal worker entrypoint
  workflows/   # Built-in Temporal workflow definitions
ui/            # React frontend (Vite + Tailwind)
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TEMPORAL_ADDRESS` | `localhost:7233` | Temporal server address |
| `TASK_QUEUE` | `default` | Temporal task queue name |
| `TZ_DEFAULT` | `UTC` | Default timezone for schedules |
| `TAPCRAFT_API_KEY` | *(auto-generated)* | API key for the web UI; auto-generated on first startup if left blank |
| `TAPCRAFT_SECRET_KEY` | | Encryption key for stored secrets |
| `GIT_REMOTE_URL` | | Optional git remote to sync generated workflow code |

See `.env.example` for a full reference.

## Development

Run formatting and type checks with:

```bash
poetry run ruff check .
poetry run mypy src
```

## Marketing Site

The `site/` directory contains a static landing page. To preview locally:

```bash
cd site && python3 -m http.server 8765
```

Deploy to GitHub Pages by pointing it at the `site/` directory.

## License

[MIT](LICENSE)
