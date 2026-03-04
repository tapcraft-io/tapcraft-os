# Tapcraft OS

Tapcraft OS is a self-hosted workflow automation platform built on [Temporal](https://temporal.io).
Define reusable activities, compose them into durable workflows with a visual graph editor,
schedule runs, and monitor execution — all from a clean web UI.

## Features

- **Visual workflow editor** – build directed acyclic graphs of activities and connect them with edges
- **Durable execution** – all workflows run on Temporal, giving you retries, timeouts, and history out of the box
- **Git-backed workspaces** – workflow code is stored in versioned workspaces and synced from git repos
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

Open http://localhost:5173. The dev server proxies API calls to `http://localhost:8001`.

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

## License

[MIT](LICENSE)
