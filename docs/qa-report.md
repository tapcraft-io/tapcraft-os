# Tapcraft QA Report

**Date:** 2026-02-07
**Tester:** Automated QA Sweep (Playwright + API curl)
**Environment:** Docker Compose (api, worker, temporal) + Vite dev server (port 5180)

---

## Executive Summary

The application is **partially functional**. Navigation, layout, and most read-only pages work well. The **critical blocker** is a database schema mismatch — the `nodes` table is missing the `activity_operation_id` column — which breaks the Workflow Editor and the Agent's ability to create workflows.

**Bugs found:** 7 (1 critical, 2 major, 4 minor)

---

## Test Results by Page

### Dashboard (`/`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | PASS | All data loads after ~2s |
| Health status cards | PASS | Temporal Connected, Worker Active, Git Synced |
| Count cards (Workflows/Activities/Runs/Schedules) | PASS | Shows 7/0/5/0 correctly |
| Count card click → navigation | PASS | Workflows card → /workflows, Runs card → /runs |
| Recent Activity table | PASS | Shows 5 runs with correct status badges |
| Upcoming Schedules section | PASS | Shows empty state correctly |
| Refresh button | PASS | Triggers data reload, all queries refetch |
| Console errors | NONE | Clean |

### Activities (`/activities`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | PASS | Empty state displayed correctly (0 activities) |
| Console errors | NONE | Clean |

### Workflows (`/workflows`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | PASS | 7 workflows listed with names, descriptions |
| Workflow card click → detail panel | PASS | Shows slug, description, recent runs |
| "Open Editor" link | FAIL | Navigates correctly but editor page is broken (see BUG-001) |
| "New" button | PASS | Links to /agent |
| Console errors | NONE | Clean |

### Workflow Editor (`/workflows/:id`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | **FAIL** | 500 error on GET /api/graphs/:id (BUG-001) |
| Error state display | PASS | Shows "Workflow not found" with back link (graceful degradation) |
| Canvas rendering | BLOCKED | Cannot test due to BUG-001 |
| Node palette | BLOCKED | Cannot test due to BUG-001 |
| Node drag/drop | BLOCKED | Cannot test due to BUG-001 |
| Edge connections | BLOCKED | Cannot test due to BUG-001 |
| Ctrl+S regenerate | BLOCKED | Cannot test due to BUG-001 |
| Node inspector | BLOCKED | Cannot test due to BUG-001 |

### Runs (`/runs`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | PASS | 5 runs displayed correctly |
| Run row click → RunDetail | PASS | Navigates to /runs/:id |
| Filter button toggle | PASS | Shows/hides filter bar |
| Status filter (Succeeded) | PASS | Filters to 1 run, shows "1 of 5 runs" |
| Status filter (Failed) | PASS | Shows empty "No matching runs" state |
| Status filter badge count | PASS | Badge shows active filter count |
| Clear filters button | PASS | Resets all filters |
| Workflow dropdown filter | PASS | Populates with workflow names |
| Console errors | NONE | Clean |

### Run Detail (`/runs/:id`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | PASS | Shows run metadata correctly |
| Breadcrumb navigation | PASS | "Runs > Run #5" with back link |
| Workflow name resolution | PASS | Shows full workflow name, links to editor |
| Status badge | PASS | Green "Succeeded" badge |
| Duration display | PASS | "608m 28s" |
| Temporal ID display | PASS | Shows full workflow ID |
| Activity Timeline | **EMPTY** | Always shows "No activity history available" (BUG-003) |
| Console errors | NONE | Clean |

### Agent (`/agent`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | PASS | Session list + welcome screen with example prompts |
| Session list | PASS | Shows all past sessions with previews and timestamps |
| Click session → load chat | PASS | Messages display correctly |
| "New conversation" button | PASS | Resets to welcome screen |
| Example prompt click | PASS | Creates new session, sends prompt as first message |
| Send message (manual) | PASS | Message sent, agent responds intelligently |
| Agent response quality | PASS | LLM provides contextual, helpful responses |
| Action cards in chat | PASS | Shows "Create Workflow" card with status |
| Delete session button | PASS | Confirmation dialog → deletes (204) |
| Agent creates workflow | **FAIL** | LLM triggers workflow creation which fails due to BUG-001 |
| validateDOMNesting error | **WARN** | Button nested inside button in AgentSessionList (BUG-002) |
| Console errors | 1 ERROR | validateDOMNesting warning (React treats as error) |

### Settings (`/settings`)
| Feature | Status | Notes |
|---------|--------|-------|
| Page load | PASS | All 4 cards render correctly |
| LLM Provider card | PASS | Shows: Configured, anthropic, claude-sonnet-4.5, **** |
| Git Configuration inputs | PASS | Remote URL and Branch editable |
| Temporal card | PASS | Address/namespace read-only, task queue editable |
| About card | PASS | Version 0.1.0, Development |
| Save button | PASS | Toast: "Settings saved successfully" |
| Task queue reset on save | **BUG** | Value resets from "tapcraft-default" to "default" (BUG-004) |
| Console errors | NONE | Clean |

---

## Bug List

### BUG-001 (CRITICAL): Missing `activity_operation_id` column in `nodes` table

**Severity:** Critical — blocks Workflow Editor and Agent workflow creation
**Affected pages:** Workflow Editor, Agent (create workflow action)
**Root cause:** The SQLAlchemy model `Node` in `src/db/models.py` defines an `activity_operation_id` column, but the corresponding Alembic migration was never applied to the actual SQLite database.

**Error:**
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: nodes.activity_operation_id
[SQL: SELECT ... FROM nodes WHERE nodes.graph_id = ?]
```

**Also affects INSERT:**
```
(sqlite3.OperationalError) table nodes has no column named activity_operation_id
[SQL: INSERT INTO nodes (graph_id, kind, label, activity_operation_id, ...) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ...]
```

**Fix:** Run an Alembic migration to add the missing columns to the `nodes` table, or manually ALTER TABLE. Need to check if other columns are also missing.

---

### BUG-002 (MINOR): validateDOMNesting — button inside button in AgentSessionList

**Severity:** Minor — React warning, no functional impact
**Location:** `ui/src/components/AgentSessionList.tsx:27`
**Error:** `Warning: validateDOMNesting(...): <button> cannot appear as a descendant of <button>`
**Root cause:** The session list item is a `<button>` and the delete icon inside it is also a `<button>`, creating invalid DOM nesting.

**Fix:** Change the outer element from `<button>` to `<div role="button">` or change the delete button to a `<span>` with onClick.

---

### BUG-003 (MAJOR): Activity Timeline always empty on Run Detail

**Severity:** Major — users cannot see step-by-step execution details
**Location:** `src/api/routers/execution.py` — `/runs/{run_id}/status` endpoint
**Symptom:** `activity_history` is always an empty array `[]` in the API response
**Root cause:** The Temporal history fetch either:
1. Returns events in a format the parser doesn't handle
2. The Temporal connection from the API container uses `temporal:7233` which may not be correctly resolving, OR
3. The workflow execution format doesn't include individual activity events in the expected structure

**Fix:** Debug the Temporal history fetch logic in the execution router. Check the raw Temporal event history format.

---

### BUG-004 (MINOR): Settings task_queue resets to "default" after save

**Severity:** Minor — config values not persisted correctly
**Location:** `src/api/server.py` — `RuntimeConfig` class
**Symptom:** The `task_queue` field shows "tapcraft-default" on initial load (from env var), but after PUT /config and re-GET, it shows "default"
**Root cause:** The `RuntimeConfig.update()` method correctly updates `self.task_queue`, but the initial value comes from `os.getenv("TASK_QUEUE", "default")`. The PUT payload from Settings sends `task_queue: "tapcraft-default"` but something in the round-trip resets it — likely the GET /config after save returns the env default because `lru_cache` returns a stale or re-initialized instance, OR the frontend isn't sending the correct field.

**Fix:** Debug the PUT → GET round-trip for task_queue. Verify the frontend sends the current form value and the backend persists it.

---

### BUG-005 (MAJOR): Agent workflow creation fails silently after first attempt

**Severity:** Major — agent cannot fulfill its primary purpose
**Location:** `src/services/agent_loop.py:141`
**Symptom:** When the agent tries to create a workflow, the DB INSERT fails (due to BUG-001), leaving the session's DB transaction in a rolled-back state. Subsequent messages in the SAME session fail with `PendingRollbackError`.
**Error:**
```
sqlalchemy.exc.PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush.
```

**Root cause:** Cascading from BUG-001. The agent_loop doesn't properly handle DB transaction rollback on workflow creation failure.

**Fix:** After fixing BUG-001, also add proper exception handling in `agent_loop.py` that catches the workflow creation error, rolls back the session, and returns a friendly error message instead of a 500.

---

### BUG-006 (MINOR): Dashboard shows "Workflow N" instead of actual names in Recent Activity

**Severity:** Minor — cosmetic
**Location:** `ui/src/pages/Dashboard.tsx`
**Symptom:** The Recent Activity table shows "Workflow 7", "Workflow 5", "Workflow 3" etc. instead of actual workflow names like "ArXiv Vision Model Research Blog Generator"
**Root cause:** The `runs` API response contains `workflow_id` but the Dashboard table just displays `Workflow ${run.workflow_id}` instead of resolving to the workflow name.

**Fix:** Either join workflow name on the backend runs endpoint, or cross-reference with the workflows data already fetched for the count cards.

---

### BUG-007 (MINOR): Example prompt creates session + sends message but action card shows "executing" forever

**Severity:** Minor — the action never resolves visually
**Location:** Agent page → example prompts
**Symptom:** When clicking an example prompt, the agent creates a session, sends the prompt, and the LLM responds with a workflow creation action. The action card shows status "executing" permanently (because workflow creation failed due to BUG-001, and the status was never updated to "error").

**Fix:** After fixing BUG-001, also ensure action status is properly updated to "completed" or "error" based on the actual outcome.

---

## Backend API Test Summary

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | 200 | Temporal connected, worker active |
| `/config` | GET | 200 | LLM configured (anthropic) |
| `/config` | PUT | 200 | Saves but task_queue may reset (BUG-004) |
| `/activities?workspace_id=1` | GET | 200 | Returns empty array |
| `/workflows?workspace_id=1` | GET | 200 | Returns 7 workflows |
| `/graphs/:id` | GET | **500** | Missing column (BUG-001) |
| `/runs?workspace_id=1` | GET | 200 | Returns 5 runs |
| `/runs/:id/status` | GET | 200 | Returns data but empty activity_history (BUG-003) |
| `/schedules?workspace_id=1` | GET | 200 | Returns empty array |
| `/agent/sessions?workspace_id=1` | GET | 200 | Returns sessions list |
| `/agent/sessions` | POST | 201 | Creates session correctly |
| `/agent/sessions/:id` | GET | 200 | Returns session with messages |
| `/agent/sessions/:id` | DELETE | 204 | Deletes correctly |
| `/agent/sessions/:id/messages` | POST | **500** | Fails when agent tries to create workflow (BUG-001/005) |
| `/agent/sessions/:id/messages` | POST | 200 | Works when agent doesn't create workflow (e.g., "what can you do?") |

---

## Priority Fix Order

1. **BUG-001** (Critical) — FIXED: Renamed `app_operation_id` → `activity_operation_id` in SQLite nodes table.
2. **BUG-005** (Major) — FIXED: Added try/except with `db.rollback()` around action execution in `agent_loop.py`.
3. **BUG-003** (Major) — FIXED: Changed Temporal event type comparisons from `.name` strings to `EventType` enum values, and fixed `event_time` from `.isoformat()` to `.ToDatetime().isoformat()`.
4. **BUG-006** (Minor) — FIXED: Dashboard now resolves workflow names from workflows data.
5. **BUG-002** (Minor) — FIXED: Changed outer `<button>` to `<div role="button">` in AgentSessionList.
6. **BUG-004** (Minor) — FIXED: Changed frontend default from "tapcraft-default" to "default" to match server env.
7. **BUG-007** (Minor) — Resolved by BUG-005 fix (action errors now produce proper error status messages).

---

## What's Working Well

- Overall navigation and layout — polished, responsive dark theme
- Dashboard with health status, count cards, and data tables
- Workflows list with detail panel sidebar
- Runs page with functional filtering (status + workflow)
- Run Detail page with metadata and breadcrumbs
- Agent chat — LLM responds intelligently, messages display correctly
- Agent session management — create, list, switch, delete all work
- Settings page — reads config, saves with toast notification
- Toast notification system — smooth animations, auto-dismiss
- Error boundaries — graceful error handling on WorkflowEditor
- Keyboard shortcut infrastructure (Ctrl+S) in place
