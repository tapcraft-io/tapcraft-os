# CLAUDE.md - Project Guidelines for AI Assistants

## CRITICAL RULES - READ FIRST

### NEVER MAKE UNAUTHORIZED CHANGES

**DO NOT SWITCH LIBRARIES, SDKS, OR FRAMEWORKS WITHOUT EXPLICIT USER APPROVAL.**

**DO NOT MAKE ARCHITECTURAL CHANGES WITHOUT EXPLICIT USER APPROVAL.**

**DO NOT "FIX" THINGS BY REPLACING THEM WITH SOMETHING ELSE.**

If something isn't working:
1. Debug it
2. Fix the actual issue
3. ASK THE USER before making any significant changes

Examples of things that require explicit approval:
- Switching from one SDK to another
- Changing database systems
- Changing build tools
- Replacing libraries
- Major refactors

### FOLLOW USER REQUIREMENTS EXACTLY

When the user asks for a workflow with specific steps, CREATE ALL THOSE STEPS.

Do not simplify. Do not reduce. Do not "optimize away" steps.

If the user asks for:
- Step 1: Browse
- Step 2: Download
- Step 3: Analyze
- Step 4: Summarize
- Step 5: Save

Then create ALL 5 STEPS, not 2.

---

## Project Overview

Tapcraft is a pure execution automation platform built on:
- **Temporal** for workflow orchestration
- **React + Vite** for the UI
- **FastAPI** for the backend
- **SQLite** for the database
- **MCP** for external tool integration (e.g., Claude Code)

## Tech Stack

- Backend: Python 3.11, FastAPI, Temporal SDK
- Frontend: React, TypeScript, Vite, Tailwind CSS
- Database: SQLite with SQLAlchemy
- Container: Docker Compose

## Key Directories

- `src/` - Backend Python code
- `src/activities/` - Temporal activities
- `src/services/` - Business logic services
- `src/api/` - FastAPI routes
- `ui/` - React frontend
- `workspace/` - Generated workflow code

## Running the Project

```bash
docker compose up -d
cd ui && npm run dev
```

- API: http://localhost:8001
- UI: http://localhost:5173
- Temporal UI: http://localhost:8082
