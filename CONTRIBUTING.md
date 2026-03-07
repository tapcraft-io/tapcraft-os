# Contributing to Tapcraft OS

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- Node.js 18+ and npm
- Docker and Docker Compose

### Getting started

```bash
# Clone the repo
git clone https://github.com/tapcraft-io/tapcraft-os.git
cd tapcraft-os

# Install Python dependencies
poetry install

# Start infrastructure (Temporal, API, Worker)
cp .env.example .env
docker compose up --build

# Install and start the UI
cd ui
npm install
npm run dev
```

### Project structure

```
src/
  api/         # FastAPI routes
  activities/  # Built-in Temporal activities
  db/          # SQLAlchemy models and migrations
  mcp/         # MCP server for agent integration
  models/      # Pydantic request/response schemas
  services/    # Business logic and CRUD
  worker/      # Temporal worker entrypoint
  workflows/   # Built-in Temporal workflows
ui/            # React + Vite + Tailwind frontend
```

## Code Style

### Python

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [mypy](https://mypy-lang.org/) for type checking:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
```

### TypeScript

```bash
cd ui
npx tsc --noEmit
```

## Submitting Changes

1. Fork the repository and create a feature branch from `main`.
2. Make your changes. Keep commits focused and well-described.
3. Ensure linting and type checks pass before pushing.
4. Open a pull request against `main` with a clear description of what changed and why.

## Reporting Issues

Open a [GitHub issue](https://github.com/tapcraft-io/tapcraft-os/issues) with:

- A clear title and description
- Steps to reproduce (if applicable)
- Expected vs. actual behavior
- Environment details (OS, Docker version, browser)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
