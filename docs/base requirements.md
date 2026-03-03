Mental Model
Tapcraft is:

A personal automation OS where users create Apps (reusable capabilities) and Workflows (Temporal flows) that orchestrate those apps.
The agent writes the code and the graph; the user can edit both via a node editor and code editor.

Apps = reusable building blocks. “Connect to my email, filter important, write to Notion” is an App.

Workflows = Temporal workflows that call Apps (and primitive steps) as nodes to accomplish a larger goal.

Graphs = node/edge representation used for the canvas UI; each App and each Workflow has a corresponding graph and backing code.

Tapcraft container (per user/tenant) holds:

all Apps

all Workflows

their graphs and code

the Agent

schedules and runs

Domain Model
2.1 Workspace

Scope for a single user or team.

id

owner_id

name

created_at, updated_at

Holds all Apps, Workflows, Schedules, Runs, AgentSessions.

2.2 App

A reusable, code-backed capability that can be invoked as a node in workflows or used standalone.

id

workspace_id

name

slug

description

category (e.g. email, crm, custom)

entrypoints: list[AppOperationRef]
(e.g. EmailClient.filter_important, NotionClient.create_page)

code_module_path (e.g. apps/email_notion_sync.py)

graph_id (for its internal graph, if you model app internals visually later)

created_at, updated_at

Apps are the thing the agent “builds” from a user description like “connect to my Gmail and Notion”.

2.3 App Operation

A callable operation exposed by an App (used as a node type).

id

app_id

name (e.g. filter_important, create_notion_page)

display_name

description

config_schema (JSON Schema for node config)

code_symbol (e.g. apps.email_notion_sync.filter_important)

2.4 Workflow

A Temporal workflow that orchestrates Apps and primitives.

id

workspace_id

name

slug

description

graph_id (the workflow graph)

code_module_path (e.g. workflows/daily_email_digest.py)

entrypoint_symbol (e.g. workflows.daily_email_digest.DailyDigestWorkflow)

created_at, updated_at

Workflows are the Temporal workflows.
Apps are called inside them as steps.

2.5 Graph

Visual representation of a Workflow or an App’s composition.

id

workspace_id

owner_type ("workflow" or "app")

owner_id (workflow_id or app_id)

nodes: Node[]

edges: Edge[]

entry_node_id

layout_metadata (zoom, pan, etc.)

version (increment on changes)

created_at, updated_at

2.6 Node

A step on the canvas.

id

graph_id

kind: "trigger" | "app_operation" | "primitive" | "logic"

label

app_operation_id (nullable; set when kind == "app_operation")

primitive_type (nullable; e.g. "http_request", "delay")

config (instance-level config; must conform to schema)

config_schema (denormalized for the UI)

ui_position: {x: number, y: number}

2.7 Edge

Connection between nodes.

id

graph_id

from_node_id

to_node_id

path (optional: "success" | "error" | custom string)

label (optional)

2.8 Schedule

Temporal schedule bound to a Workflow.

id

workflow_id

name

cron

timezone

enabled: bool

next_run_at, last_run_at

2.9 Run

Single workflow execution.

id

workflow_id

workspace_id

status: "queued" | "running" | "succeeded" | "failed"

started_at, ended_at

summary (short text)

error_excerpt (if failed)

input_config (workflow inputs at runtime)

2.10 AgentSession

Interaction with the agent to create/modify Apps or Workflows.

id

workspace_id

target_type: "app" | "workflow"

target_id (nullable when creating)

mode: "create" | "modify" | "debug"

user_prompt

plan (structured object)

graph_diff (before/after node/edge changes)

code_diff_summary

status: "draft" | "applied" | "rejected"

created_at, updated_at

System Architecture
3.1 Components

Tapcraft Frontend (React)

Node editor canvas (graphs)

Agent UI

Apps / Workflows / Schedules / Runs screens

Tapcraft API (FastAPI)

CRUD for Apps, Workflows, Graphs, Schedules, Runs, AgentSessions

Integration with Temporal (start workflows, manage schedules)

Integration with Git (code persistence)

Integration with LLM (pydantic-ai Agent)

Temporal Server

Runs workflow executions, schedules, retries.

Temporal Worker (Python)

Imports generated code modules for workflows and app operations.

Registers Temporal workflows.

Exposes activities (HTTP, email clients, Notion clients, etc.).

Git Repo

Stores app and workflow code under the user’s workspace.

Example layout:

/workspace/<user-or-tenant>/
apps/
email_notion_sync.py
workflows/
daily_email_digest.py

LLM Agent Service (pydantic-ai)

Planner: task → Plan

Generator: Plan + context → code module + graph structure

Repair: errors or validation issues → patch

3.2 Data Flow: “Create app via agent”

User: “Create an app that connects to my email, filters important emails, and posts to Notion with sentiment.”

Frontend → API:

POST /agent/sessions with target_type="app", mode="create", and user_prompt.

API → AgentService:
Passes prompt + known primitives (available email client, Notion client, etc.).

AgentService:
Returns:

plan

app_code_module_text

app_operations (names, config schemas)

API:
Writes apps/<slug>.py to disk.

Creates App + AppOperation records.

Commits to Git.

User sees new App in Apps list and can inspect in Graph editor (if you choose to also graph its internals later).
3.3 Data Flow: “Create workflow via agent”

User: “Every morning, run my email → Notion app, then send me a summary on Slack.”

Frontend → API: similar AgentSession with target_type="workflow".

AgentService:

Reads existing Apps and operations.

Outputs:

graph: {nodes, edges} (nodes referencing AppOperations & primitives)

workflow_code_module_text

entrypoint_symbol

API:
Writes workflows/<slug>.py

Creates Workflow + Graph records, Nodes & Edges.

Validates code (determinism, imports).

Registers workflow in worker.

User is dropped into Workflow Graph editor with the generated graph and can tweak nodes and code.
LLM Agent Behavior (pydantic-ai)
4.1 Inputs

Agent receives:

target_type: "app" or "workflow"

existing_apps (only for workflow generation)

primitives (HTTP, delay, email client, Slack client, etc.)

user_prompt

For modify mode: current graph + code excerpt + error summary (if debugging).

4.2 Outputs for target_type="app"

app_module_text

Contains a main App class or module-level functions (operations).

operations: AppOperationSpec[]

name

description

config_schema

code_symbol (function/method name)

Optional: internal graph (if you support visualizing App internals later).

4.3 Outputs for target_type="workflow"

graph: {nodes: NodeSpec[], edges: EdgeSpec[], entry_node_id}

workflow_module_text

Temporal workflow class @workflow.defn with run(self, cfg: dict) orchestrating node steps.

manifest for worker:

entrypoint_symbol

config_schema

4.4 Rules (prompt constraints)

Workflows:

No network/FS/LLM calls directly inside workflow logic; call helper functions/activities instead.

Use known App operations as steps.

Keep orchestration explicit and linear or clearly branched.

Apps:

Implement API calls cleanly (SDK or HTTP).

Surface configuration as config_schema.

Avoid hardcoding secrets.

Graph:

Every node maps to a concrete function in code or known primitive.

Edges represent control flow (and optionally pass data).

4.5 Repair

For modify/debug mode:

Input:

current code

graph

error summary (from a failed run)

Output:

patched code

updated graph nodes/edges if needed

Always produce a diff summary for the UI.

UX Spec (Andor-style, with node editor)
5.1 Global Layout

Left sidebar (standard, self-explanatory labels):

Home

Apps

Workflows

Agent

Runs

Settings

Main content area: panel for the current section.

Style:

Dark, muted color palette (steel gray, off-black).

Accents: subdued orange/green/blue for status and selection.

Typography: Inter / SF Pro; 13–14px body, 16–18px titles.

Slightly rounded panels (4–6px), no flashy gradients, subtle noise.

5.2 Home

System status:

Temporal connection (OK/error)

Worker status

Git sync status

Next scheduled runs (workflow name, time)

Recent runs (status badges)

Purpose: “Is my OS healthy and what’s about to happen?”

5.3 Apps

Apps List:

Columns: Name, Description, Last modified, #Operations.

Actions: “Create app with agent”, “Open”.

App Detail:

Tabs:

Overview
Name, description.

List of operations (name, description, config schema summary).

Buttons: “Ask agent to modify this app”, “Open in code editor”.

Code
File browser scoped to apps/<slug>.py and related files.

Monaco editor pane.

“Manual edit” toggle (on change → dirty state → commit button).

Usage
Workflows that use this app.

Quick navigation to those workflows.

Later (optional): App-level graph if you want internal node representation.

5.4 Workflows

Workflows List:

Columns: Name, Description, Last run, Status (has schedule / none).

Actions: “Create workflow with agent”, “Open”.

Workflow Editor (node editor):

3-pane layout:

Left: Palette

Sections:

Triggers (cron, webhook, HTTP, email)

App operations (grouped by App)

Primitives (HTTP request, delay, log, branch)

Drag to canvas to add a node.

Center: Canvas

Nodes rendered as simple cards:

Title (operation name)

Icon (type)

Status indicator (last run: ok/fail/never)

Edges: straight or slightly curved lines.

Zoom/pan.

No cartoon cables; aim for thin lines, subtle arrows.

Right: Inspector

Node tab:

Node name, label

Type (App / Trigger / Primitive)

Config form (generated from config_schema)

Code tab:

Function code for this node (if you choose that granularity) or snippet view from module.

Workflow tab:

Summary of workflow config (inputs, outputs)

Link to full workflow code.

Bottom bar:

Left: “Run once”, “Validate”, status messages.

Right: “Ask agent to modify…”, “Save & commit”, “View runs”.

5.5 Agent screen

Global view for all AgentSessions.

Left: Session list (App/Workflow, mode, status).

Center: Conversation & plan:

Textarea for new instructions.

Plan view: steps, APIs, risks.

Status of generation/validation/repair.

Right: Context:

Selected App/Workflow info.

Available primitives.

From here, user can:

Start a new App or Workflow generation.

Attach session to an existing App/Workflow for modification.

5.6 Runs

Table:

Run ID, Workflow, App (if applicable), status, start time, duration.

Filters: by workflow, by status, by time.

Detail:

High-level info.

Activity timeline.

Error excerpt.

Link to Temporal Web.

5.7 Settings

Sections:

LLM: models, rate limits.

Temporal: namespace, address.

Git: remote, branch, author.

Runtime: container image used by worker.

Secrets: list of configured secret keys (masked).

Backend API Surface (high-level)
You don’t need every endpoint spelled out, but for Codex, group by resource:

/apps: CRUD, operations list, link to code module.

/workflows: CRUD, link to graph & code.

/graphs: CRUD for graph JSON (nodes, edges, layout).

/nodes, /edges: usually manipulated via /graphs.

/schedules: CRUD for workflow schedules (maps to Temporal schedules).

/runs: list, detail, link to Temporal IDs.

/agent/sessions: create, update, list; endpoints to call plan/generate/repair.

/code: read/write files, validate modules, commit to Git.

/settings: read/update LLM, Temporal, Git config.

Temporal Integration
Each Workflow has a single Temporal workflow class as entrypoint.

Worker:

On boot or reload, scans workflows/ directory, imports modules, registers @workflow.defn classes.

Schedule:

Schedule.workflow_id ↔ Temporal schedule name.

Workflow execution:

Orchestrator uses a node execution engine that walks the graph (in order) and invokes:

App operations,

primitive functions (HTTP, delay, etc.),

branches based on node outputs.

Graph → code synchronization is handled by:

A template or engine that regenerates orchestrator logic from the graph and re-writes the module when graph changes (for v1, a simple “nodes in topological order” + basic condition support is enough).

Implementation Milestones for Codex
Very summarized, to avoid another giant task list:

Domain + API basics
Models & tables for Workspace, App, AppOperation, Workflow, Graph, Node, Edge, Schedule, Run, AgentSession.

CRUD routes for Apps, Workflows, Graphs, Schedules, Runs.

Temporal + Worker
Worker that loads workflow modules from workflows/.

TemporalService that can start workflows and manage schedules.

Code persistence
Service to read/write apps/.py and workflows/.py, with Git commit & push.

Agent integration
pydantic-ai based AgentService that takes:

target_type, user_prompt, existing Apps & primitives

outputs: app/workflow code and graph (for workflows).

Validation layer (imports, determinism, existence of referenced operations).

Apps UI
Apps list + detail (operations & code).

Workflows UI
Workflows list.

Graph editor (nodes, edges, inspector).

Code view.

Agent UI
Agent screen + inline “Ask agent to modify” from App/Workflow detail.

Schedules & Runs UI
Schedule CRUD.

Runs table & detail.

Show less