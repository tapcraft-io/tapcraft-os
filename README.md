# Tapcraft OS

Tapcraft OS is a single-tenant automation platform that turns natural language prompts into
durable Temporal workflows. Automations are versioned in Git, leverage MCP-discovered tools,
and execute via a dedicated worker process.

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+

### Install dependencies

```bash
poetry install
```

### Environment

Copy `.env.example` to `.env` and adjust values as needed. The default configuration expects Temporal to be
available at `localhost:7233` and uses the `default` task queue.

### Running the stack

The project ships with a docker-compose configuration that starts Temporal, the API service,
and the worker:

```bash
docker compose up --build
```

Temporal Web will be available at http://localhost:8080 and the FastAPI application at
http://localhost:8000.

### Rebel Control Center UI

The `ui/` workspace hosts the Star-Wars-meets-macOS Control Center. It is a Vite + React +
Tailwind application that targets the FastAPI backend. Install dependencies and start the
development server with:

```bash
cd ui
npm install
npm run dev
```

The dev server proxies API calls to `http://localhost:8000`. Open http://localhost:5173 to explore
the Command Deck, Patch Bay, Agent Console, Chrono-Scope, and Config panels.

## Project Layout

```
src/
  api/         # FastAPI application
  services/    # Integration and domain services
  models/      # Shared pydantic models
  generated/   # Agent-authored workflow modules
  agent/       # Prompt templates surfaced to the agent
  worker/      # Temporal worker entrypoint
```

## LLM Agent Layer

The API now exposes a multi-step LLM flow that covers planning, code generation, validation,
repair, testing, and decision memory:

- `POST /agent/plan` – produce a `PlanDoc` outlining steps, risks, and artifacts.
- `POST /agent/generate` – turn a prompt + plan into a Temporal workflow module and manifest.
- `POST /agent/validate` – run deterministic guardrails and receive diagnostics.
- `POST /agent/repair` – apply lightweight auto-fixes based on validation issues or runtime logs.
- `POST /agent/tests` – request pytest scaffolding for the generated module.
- `GET/POST /agent/memory/{workflow_ref}` – persist decision history and summaries per workflow.
- `GET /agent/templates` – inspect task-specific plan templates stored under `src/agent/templates/`.
- `GET/PUT /agent/models` & `GET/PUT /agent/limits` – control model selection, token budgets, and rate
  limits for each agent stage.

Capabilities are cached server-side. Use `POST /config/capabilities/refresh` to rebuild the list
and `GET /config/capabilities/schema/{tool_id}` to inspect JSON Schemas used for prompting.

### Agent Environment Variables

The `.env.example` file documents additional knobs for the agent layer, including default model
choices, token budgets, rate limits, and plan cache TTL. Copy values into `.env` to customize them
per environment.

## Development Tasks

The MVP roadmap is organized into sprints. Begin with the core loop:
1. Implement shared models in `src/models/core.py`.
2. Build the Temporal service client in `src/services/temporal_service.py`.
3. Stand up the worker skeleton in `src/worker/worker.py`.
4. Expose initial API routes from `src/api/server.py`.

Run formatting and type checks with:

```bash
poetry run ruff check .
poetry run mypy src
```

## License

MIT
