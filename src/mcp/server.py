"""Tapcraft MCP server — exposes workflows, runs, activities, secrets, and schedules
to Claude Code via the Model Context Protocol.

Run locally:
    python -m src.mcp.server

Add to Claude Code MCP config (~/.claude/claude_desktop_config.json):
    {
        "mcpServers": {
            "tapcraft": {
                "command": "python",
                "args": ["-m", "src.mcp.server"],
                "cwd": "/path/to/tapcraft-os",
                "env": {
                    "DATABASE_URL": "sqlite+aiosqlite:///./tapcraft.db",
                    "TEMPORAL_ADDRESS": "localhost:7233"
                }
            }
        }
    }
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging — MCP stdio reserves stdout for JSON-RPC, so log to stderr
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger("tapcraft.mcp")

# ---------------------------------------------------------------------------
# Workspace ID — most crud operations need one.  Default to 1 (single-tenant).
# Override via TAPCRAFT_WORKSPACE_ID env var.
# ---------------------------------------------------------------------------
WORKSPACE_ID = int(os.getenv("TAPCRAFT_WORKSPACE_ID", "1"))
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent / "workspace"

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "tapcraft",
    instructions=(
        "Tapcraft is a self-hosted workflow automation platform built on Temporal. "
        "Use the tapcraft tools to list, deploy, run, and monitor workflows. "
        "Read the tapcraft://docs/* resources first to understand how to write "
        "correct Temporal workflows and activities for Tapcraft."
    ),
)


# ===== helpers =============================================================


async def _get_db():
    """Get a fresh async DB session."""
    from src.db.base import AsyncSessionLocal

    return AsyncSessionLocal()


async def _get_temporal_client():
    """Connect to the Temporal server."""
    from temporalio.client import Client

    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    return await Client.connect(address)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _safe_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


# ===== MCP Tools ===========================================================

# ---- Workflows ------------------------------------------------------------


@mcp.tool()
async def tapcraft_list_workflows() -> str:
    """List all workflows with name, slug, status, and last run info."""
    from src.services import crud

    db = await _get_db()
    try:
        workflows = await crud.list_workflows(db, WORKSPACE_ID)
        result = []
        for w in workflows:
            runs = await crud.list_runs(db, WORKSPACE_ID, workflow_id=w.id)
            last_run = runs[0] if runs else None
            result.append(
                {
                    "id": w.id,
                    "name": w.name,
                    "slug": w.slug,
                    "description": w.description,
                    "code_module_path": w.code_module_path,
                    "entrypoint_symbol": w.entrypoint_symbol,
                    "created_at": _iso(w.created_at),
                    "last_run": {
                        "id": last_run.id,
                        "status": last_run.status,
                        "started_at": _iso(last_run.started_at),
                        "ended_at": _iso(last_run.ended_at),
                    }
                    if last_run
                    else None,
                }
            )
        return json.dumps(result, indent=2)
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_get_workflow(workflow_id: int) -> str:
    """Get workflow details including its current code.

    Args:
        workflow_id: The ID of the workflow to retrieve.
    """
    from src.services import crud

    db = await _get_db()
    try:
        wf = await crud.get_workflow(db, workflow_id, load_graph=True)
        if not wf:
            return json.dumps({"error": f"Workflow {workflow_id} not found"})

        # Read the source code file
        code = ""
        code_path = WORKSPACE_ROOT / wf.code_module_path.replace(".", "/").rsplit(".", 1)[0]
        # Try common extensions
        for suffix in [".py", ""]:
            p = Path(str(code_path) + suffix)
            if p.exists():
                code = p.read_text()
                break

        # Also try the module path directly
        if not code:
            parts = wf.code_module_path.split(".")
            candidate = WORKSPACE_ROOT / "/".join(parts[1:]) if parts[0] == "workspace" else None
            if candidate:
                py_path = candidate.with_suffix(".py")
                if py_path.exists():
                    code = py_path.read_text()

        graph_data = None
        if wf.graph:
            graph_data = {
                "id": wf.graph.id,
                "version": wf.graph.version,
                "nodes": [
                    {
                        "id": n.id,
                        "kind": n.kind,
                        "label": n.label,
                        "primitive_type": n.primitive_type,
                        "config": _safe_json(n.config),
                    }
                    for n in (wf.graph.nodes or [])
                ],
                "edges": [
                    {
                        "id": e.id,
                        "from_node_id": e.from_node_id,
                        "to_node_id": e.to_node_id,
                        "label": e.label,
                    }
                    for e in (wf.graph.edges or [])
                ],
            }

        return json.dumps(
            {
                "id": wf.id,
                "name": wf.name,
                "slug": wf.slug,
                "description": wf.description,
                "code_module_path": wf.code_module_path,
                "entrypoint_symbol": wf.entrypoint_symbol,
                "code": code,
                "graph": graph_data,
                "created_at": _iso(wf.created_at),
            },
            indent=2,
        )
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_deploy_workflow(
    slug: str,
    name: str,
    code: str,
    description: str = "",
) -> str:
    """Deploy a Temporal workflow by writing Python code to the workspace and
    registering it in the database.

    IMPORTANT: Read tapcraft://docs/writing-workflows first to understand
    the correct patterns.

    Args:
        slug: URL-safe identifier (e.g. "daily-metrics"). Must be unique.
        name: Human-readable name.
        code: Complete Python module code for the workflow. Must contain a
              @workflow.defn class with a @workflow.run method.
        description: Optional description of what the workflow does.
    """
    from src.services import crud

    db = await _get_db()
    try:
        # Determine the workflow class name from the code
        class_name = None
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("class ") and ":" in stripped:
                class_name = stripped.split("class ")[1].split("(")[0].split(":")[0].strip()
                break

        if not class_name:
            return json.dumps({"error": "Could not find a class definition in the provided code."})

        # Write code to workspace
        ws_dir = WORKSPACE_ROOT / f"workspace_{WORKSPACE_ID}" / "workflows"
        ws_dir.mkdir(parents=True, exist_ok=True)

        # Ensure __init__.py files exist
        for d in [WORKSPACE_ROOT / f"workspace_{WORKSPACE_ID}", ws_dir]:
            init = d / "__init__.py"
            if not init.exists():
                init.write_text("")

        module_filename = slug.replace("-", "_") + ".py"
        module_path = ws_dir / module_filename
        module_path.write_text(code)

        # Module path for import: workspace.workspace_N.workflows.module_name
        module_stem = module_filename.replace(".py", "")
        entrypoint = f"workspace.workspace_{WORKSPACE_ID}.workflows.{module_stem}.{class_name}"
        code_module = f"workspace.workspace_{WORKSPACE_ID}.workflows.{module_stem}"

        # Create a graph for the workflow (required by schema)
        graph = await crud.create_graph(db, WORKSPACE_ID, owner_type="workflow", owner_id=0)

        # Check if workflow with this slug already exists
        existing_workflows = await crud.list_workflows(db, WORKSPACE_ID)
        existing = next((w for w in existing_workflows if w.slug == slug), None)

        if existing:
            # Update existing workflow code on disk (already written above)
            await crud.update_workflow(db, existing.id, name=name, description=description)
            await db.commit()
            return json.dumps(
                {
                    "status": "updated",
                    "workflow_id": existing.id,
                    "slug": slug,
                    "entrypoint": existing.entrypoint_symbol,
                    "code_path": str(module_path),
                    "message": f"Updated workflow '{name}'. Code written to {module_path}.",
                }
            )

        # Create new workflow
        wf = await crud.create_workflow(
            db,
            workspace_id=WORKSPACE_ID,
            name=name,
            slug=slug,
            graph_id=graph.id,
            code_module_path=code_module,
            entrypoint_symbol=entrypoint,
            description=description,
        )

        return json.dumps(
            {
                "status": "created",
                "workflow_id": wf.id,
                "slug": slug,
                "entrypoint": entrypoint,
                "code_path": str(module_path),
                "message": f"Deployed workflow '{name}'. Code written to {module_path}. "
                f"Use tapcraft_run_workflow to execute it.",
            }
        )
    finally:
        await db.close()


# ---- Runs -----------------------------------------------------------------


@mcp.tool()
async def tapcraft_run_workflow(
    workflow_id: int,
    input_config: dict | None = None,
) -> str:
    """Execute a workflow with the given input config.

    Args:
        workflow_id: The ID of the workflow to run.
        input_config: Optional dict of config values passed to the workflow's run method.
    """
    from src.services import crud

    db = await _get_db()
    try:
        wf = await crud.get_workflow(db, workflow_id)
        if not wf:
            return json.dumps({"error": f"Workflow {workflow_id} not found"})

        input_cfg = input_config or {}
        temporal_wf_id = f"workflow-{wf.slug}-{uuid.uuid4().hex[:8]}"

        run = await crud.create_run(
            db,
            workspace_id=wf.workspace_id,
            workflow_id=wf.id,
            input_config=json.dumps(input_cfg),
            temporal_workflow_id=temporal_wf_id,
        )

        # Start on Temporal
        try:
            client = await _get_temporal_client()
            module_path, class_name = wf.entrypoint_symbol.rsplit(".", 1)
            mod = importlib.import_module(module_path)
            workflow_class = getattr(mod, class_name)

            task_queue = os.getenv("TASK_QUEUE", "default")
            await client.start_workflow(
                workflow_class.run,
                input_cfg,
                id=temporal_wf_id,
                task_queue=task_queue,
            )
            await crud.update_run(db, run.id, status="running")

            return json.dumps(
                {
                    "run_id": run.id,
                    "workflow_id": wf.id,
                    "temporal_workflow_id": temporal_wf_id,
                    "status": "running",
                }
            )
        except Exception as e:
            await crud.update_run(db, run.id, status="failed", error_excerpt=str(e)[:500])
            return json.dumps(
                {
                    "run_id": run.id,
                    "status": "failed",
                    "error": str(e),
                }
            )
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_get_run(run_id: int) -> str:
    """Get run status, step results, errors, and timing.

    Args:
        run_id: The ID of the run to retrieve.
    """
    from src.services import crud

    db = await _get_db()
    try:
        run = await crud.get_run(db, run_id)
        if not run:
            return json.dumps({"error": f"Run {run_id} not found"})

        result = {
            "id": run.id,
            "workflow_id": run.workflow_id,
            "status": run.status,
            "started_at": _iso(run.started_at),
            "ended_at": _iso(run.ended_at),
            "summary": run.summary,
            "error_excerpt": run.error_excerpt,
            "input_config": _safe_json(run.input_config),
            "temporal_workflow_id": run.temporal_workflow_id,
        }

        # Try to fetch activity history from Temporal
        if run.temporal_workflow_id and run.status in ("running", "succeeded", "failed"):
            try:
                client = await _get_temporal_client()
                handle = client.get_workflow_handle(run.temporal_workflow_id)

                from temporalio.api.enums.v1 import WorkflowExecutionStatus, EventType

                desc = await handle.describe()
                wf_status = desc.status
                if wf_status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_COMPLETED:
                    new_status = "succeeded"
                elif wf_status == WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_CANCELED:
                    new_status = "cancelled"
                elif wf_status in (
                    WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_FAILED,
                    WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TERMINATED,
                    WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_TIMED_OUT,
                ):
                    new_status = "failed"
                else:
                    new_status = "running"

                if new_status != run.status:
                    await crud.update_run(db, run.id, status=new_status)
                    result["status"] = new_status

                # Fetch activity history
                history = await handle.fetch_history()
                activity_scheduled = {}
                activity_history = []

                for event in history.events:
                    et = event.event_type
                    if et == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
                        attrs = event.activity_task_scheduled_event_attributes
                        activity_scheduled[event.event_id] = {
                            "activity_name": attrs.activity_type.name,
                            "scheduled_at": event.event_time.ToDatetime().isoformat()
                            if event.event_time
                            else None,
                            "scheduled_event_id": event.event_id,
                        }
                    elif et == EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED:
                        attrs = event.activity_task_completed_event_attributes
                        sid = attrs.scheduled_event_id
                        if sid in activity_scheduled:
                            info = activity_scheduled[sid]
                            info["status"] = "completed"
                            info["ended_at"] = (
                                event.event_time.ToDatetime().isoformat()
                                if event.event_time
                                else None
                            )
                            activity_history.append(info)
                    elif et == EventType.EVENT_TYPE_ACTIVITY_TASK_FAILED:
                        attrs = event.activity_task_failed_event_attributes
                        sid = attrs.scheduled_event_id
                        if sid in activity_scheduled:
                            info = activity_scheduled[sid]
                            info["status"] = "failed"
                            info["error"] = str(attrs.failure.message) if attrs.failure else None
                            activity_history.append(info)

                # Still-running activities
                completed_ids = {a.get("scheduled_event_id") for a in activity_history}
                for sid, info in activity_scheduled.items():
                    if sid not in completed_ids:
                        info["status"] = "running"
                        activity_history.append(info)

                result["activity_history"] = activity_history

            except Exception as e:
                result["temporal_error"] = str(e)

        return json.dumps(result, indent=2)
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_list_runs(
    workflow_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
) -> str:
    """List recent runs, optionally filtered by workflow or status.

    Args:
        workflow_id: Filter by workflow ID.
        status: Filter by status (queued, running, succeeded, failed, cancelled).
        limit: Maximum number of runs to return (default 20).
    """
    from src.services import crud

    db = await _get_db()
    try:
        runs = await crud.list_runs(db, WORKSPACE_ID, workflow_id=workflow_id, status=status)
        runs = runs[:limit]
        result = []
        for r in runs:
            result.append(
                {
                    "id": r.id,
                    "workflow_id": r.workflow_id,
                    "status": r.status,
                    "started_at": _iso(r.started_at),
                    "ended_at": _iso(r.ended_at),
                    "error_excerpt": r.error_excerpt,
                    "temporal_workflow_id": r.temporal_workflow_id,
                    "created_at": _iso(r.created_at),
                }
            )
        return json.dumps(result, indent=2)
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_retry_run(run_id: int, input_config: dict | None = None) -> str:
    """Retry a failed or cancelled run.

    Args:
        run_id: The ID of the run to retry.
        input_config: Optional override for the input config. If not provided,
                      reuses the original run's config.
    """
    from src.services import crud

    db = await _get_db()
    try:
        run = await crud.get_run(db, run_id)
        if not run:
            return json.dumps({"error": f"Run {run_id} not found"})

        if run.status not in ("failed", "cancelled"):
            return json.dumps(
                {
                    "error": f"Cannot retry run with status '{run.status}'. "
                    f"Only failed or cancelled runs can be retried."
                }
            )

        wf = await crud.get_workflow(db, run.workflow_id)
        if not wf:
            return json.dumps({"error": "Original workflow not found"})

        if input_config is not None:
            cfg = input_config
            cfg_str = json.dumps(cfg)
        else:
            cfg_str = run.input_config or "{}"
            cfg = _safe_json(cfg_str)
            if isinstance(cfg, str):
                cfg = {}

        temporal_wf_id = f"workflow-{wf.slug}-{uuid.uuid4().hex[:8]}"

        new_run = await crud.create_run(
            db,
            workspace_id=run.workspace_id,
            workflow_id=run.workflow_id,
            input_config=cfg_str,
            temporal_workflow_id=temporal_wf_id,
        )

        try:
            client = await _get_temporal_client()
            module_path, class_name = wf.entrypoint_symbol.rsplit(".", 1)
            mod = importlib.import_module(module_path)
            workflow_class = getattr(mod, class_name)
            task_queue = os.getenv("TASK_QUEUE", "default")

            await client.start_workflow(
                workflow_class.run,
                cfg,
                id=temporal_wf_id,
                task_queue=task_queue,
            )
            await crud.update_run(db, new_run.id, status="running")

            return json.dumps(
                {
                    "new_run_id": new_run.id,
                    "original_run_id": run_id,
                    "temporal_workflow_id": temporal_wf_id,
                    "status": "running",
                }
            )
        except Exception as e:
            await crud.update_run(db, new_run.id, status="failed", error_excerpt=str(e)[:500])
            return json.dumps({"new_run_id": new_run.id, "status": "failed", "error": str(e)})
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_cancel_run(run_id: int) -> str:
    """Cancel a running workflow execution.

    Args:
        run_id: The ID of the run to cancel.
    """
    from src.services import crud

    db = await _get_db()
    try:
        run = await crud.get_run(db, run_id)
        if not run:
            return json.dumps({"error": f"Run {run_id} not found"})

        if run.status not in ("queued", "running"):
            return json.dumps(
                {
                    "error": f"Cannot cancel run with status '{run.status}'. "
                    f"Only queued or running runs can be cancelled."
                }
            )

        if not run.temporal_workflow_id:
            await crud.update_run(db, run.id, status="cancelled", error_excerpt="Cancelled by user")
            return json.dumps(
                {
                    "run_id": run.id,
                    "status": "cancelled",
                    "message": "Cancelled (not yet on Temporal)",
                }
            )

        try:
            client = await _get_temporal_client()
            handle = client.get_workflow_handle(run.temporal_workflow_id)
            try:
                await handle.cancel()
            except Exception:
                await handle.terminate(reason="Cancelled via Tapcraft MCP")

            await crud.update_run(db, run.id, status="cancelled", error_excerpt="Cancelled by user")
            return json.dumps(
                {"run_id": run.id, "status": "cancelled", "message": "Cancelled successfully"}
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to cancel: {e}"})
    finally:
        await db.close()


# ---- Activities -----------------------------------------------------------


@mcp.tool()
async def tapcraft_list_activities() -> str:
    """List all available activities with their config schemas.

    Returns built-in platform activities and any user-registered activities.
    """
    from src.services import crud

    db = await _get_db()
    try:
        activities = await crud.list_activities(db, WORKSPACE_ID)

        # Start with built-in activities
        result = [
            {
                "name": "net.http.request",
                "type": "built-in",
                "description": "Execute a single HTTP request",
                "config_schema": {
                    "method": "HTTP method (GET, POST, PUT, DELETE, etc.)",
                    "url": "Target URL",
                    "headers": "Optional dict of HTTP headers",
                    "body": "Optional request body",
                },
            },
            {
                "name": "net.http.parallel",
                "type": "built-in",
                "description": "Run multiple HTTP requests in parallel",
                "config_schema": {
                    "requests": "List of request dicts (method, url, headers, body, label)",
                    "timeout": "Per-request timeout in seconds (default 30)",
                },
            },
            {
                "name": "feed.rss.read",
                "type": "built-in",
                "description": "Fetch and parse an RSS/Atom feed",
                "config_schema": {
                    "url": "Feed URL to fetch",
                    "max_items": "Maximum items to return (default 20)",
                },
            },
            {
                "name": "data.parse_xml",
                "type": "built-in",
                "description": "Parse XML string into nested dict",
                "config_schema": {
                    "xml_string": "Raw XML content to parse",
                },
            },
            {
                "name": "data.dedup",
                "type": "built-in",
                "description": "Deduplicate a list of dicts by a key field",
                "config_schema": {
                    "items": "List of dicts to deduplicate",
                    "key_field": "Dict key used to determine uniqueness",
                },
            },
            {
                "name": "files.read",
                "type": "built-in",
                "description": "Read a file from the workspace",
                "config_schema": {
                    "path": "File path to read",
                },
            },
            {
                "name": "files.write",
                "type": "built-in",
                "description": "Write content to a file in the workspace",
                "config_schema": {
                    "path": "File path to write",
                    "content": "Content to write",
                },
            },
        ]

        # Add user-registered activities
        for act in activities:
            for op in act.operations:
                result.append(
                    {
                        "name": op.code_symbol,
                        "type": "user",
                        "display_name": op.display_name,
                        "description": op.description,
                        "config_schema": _safe_json(op.config_schema),
                        "activity_id": act.id,
                        "operation_id": op.id,
                    }
                )

        return json.dumps(result, indent=2)
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_get_activity_schema(activity_name: str) -> str:
    """Get full input/output schema for an activity.

    Args:
        activity_name: The activity name (e.g. 'net.http.request', 'feed.rss.read').
    """
    # Built-in activity schemas
    builtin_schemas = {
        "net.http.request": {
            "name": "net.http.request",
            "description": "Execute a single HTTP request",
            "input_schema": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method", "default": "GET"},
                    "url": {"type": "string", "description": "Target URL"},
                    "headers": {"type": "object", "description": "HTTP headers dict"},
                    "body": {"description": "Request body (string or JSON)"},
                },
                "required": ["url"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "status_code": {"type": "integer"},
                    "body": {"type": "string"},
                    "headers": {"type": "object"},
                },
            },
        },
        "net.http.parallel": {
            "name": "net.http.parallel",
            "description": "Run multiple HTTP requests in parallel via asyncio.gather",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "method": {"type": "string", "default": "GET"},
                                "url": {"type": "string"},
                                "headers": {"type": "object"},
                                "body": {},
                                "label": {"type": "string"},
                            },
                            "required": ["url"],
                        },
                    },
                    "timeout": {"type": "number", "default": 30},
                },
                "required": ["requests"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "count": {"type": "integer"},
                },
            },
        },
        "feed.rss.read": {
            "name": "feed.rss.read",
            "description": "Fetch and parse an RSS or Atom feed",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Feed URL"},
                    "max_items": {"type": "integer", "default": 20},
                },
                "required": ["url"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "items": {"type": "array"},
                    "count": {"type": "integer"},
                },
            },
        },
        "data.parse_xml": {
            "name": "data.parse_xml",
            "description": "Parse an XML string into a nested dict",
            "input_schema": {
                "type": "object",
                "properties": {
                    "xml_string": {"type": "string", "description": "Raw XML to parse"},
                },
                "required": ["xml_string"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "result": {"type": "object"},
                },
            },
        },
        "data.dedup": {
            "name": "data.dedup",
            "description": "Deduplicate a list of dicts by a key field",
            "input_schema": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "description": "List of dicts"},
                    "key_field": {"type": "string", "description": "Key for uniqueness"},
                },
                "required": ["items", "key_field"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "items": {"type": "array"},
                    "count": {"type": "integer"},
                    "duplicates_removed": {"type": "integer"},
                },
            },
        },
        "files.read": {
            "name": "files.read",
            "description": "Read a file from the workspace filesystem",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
        },
        "files.write": {
            "name": "files.write",
            "description": "Write content to a file in the workspace",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "path": {"type": "string"},
                },
            },
        },
    }

    if activity_name in builtin_schemas:
        return json.dumps(builtin_schemas[activity_name], indent=2)

    # Search user activities in DB
    from src.services import crud

    db = await _get_db()
    try:
        activities = await crud.list_activities(db, WORKSPACE_ID)
        for act in activities:
            for op in act.operations:
                if op.code_symbol == activity_name:
                    return json.dumps(
                        {
                            "name": op.code_symbol,
                            "display_name": op.display_name,
                            "description": op.description,
                            "config_schema": _safe_json(op.config_schema),
                            "activity_id": act.id,
                            "operation_id": op.id,
                        },
                        indent=2,
                    )
        return json.dumps({"error": f"Activity '{activity_name}' not found"})
    finally:
        await db.close()


# ---- Secrets --------------------------------------------------------------


@mcp.tool()
async def tapcraft_manage_secret(
    action: str,
    name: str,
    value: str | None = None,
    category: str | None = None,
) -> str:
    """Create, update, delete, or list secrets.

    Secrets are encrypted at rest and available to activities at runtime
    via the secrets service.

    Args:
        action: One of 'set', 'delete', or 'list'. Use 'set' to create or update.
        name: Secret name (ignored for 'list').
        value: Secret value (required for 'set').
        category: Optional category label.
    """
    from src.services import secrets as secrets_svc

    db = await _get_db()
    try:
        if action == "list":
            secret_list = await secrets_svc.list_secrets(db)
            result = [
                {"name": s.name, "category": s.category, "created_at": _iso(s.created_at)}
                for s in secret_list
            ]
            await db.commit()
            return json.dumps(result, indent=2)

        elif action == "set":
            if not value:
                return json.dumps({"error": "value is required for 'set' action"})
            await secrets_svc.set_secret(db, name=name, value=value, category=category)
            await db.commit()
            return json.dumps({"status": "ok", "message": f"Secret '{name}' saved"})

        elif action == "delete":
            deleted = await secrets_svc.delete_secret(db, name=name)
            await db.commit()
            if deleted:
                return json.dumps({"status": "ok", "message": f"Secret '{name}' deleted"})
            return json.dumps({"error": f"Secret '{name}' not found"})

        else:
            return json.dumps(
                {"error": f"Unknown action '{action}'. Use 'set', 'delete', or 'list'."}
            )
    finally:
        await db.close()


# ---- Schedules ------------------------------------------------------------


@mcp.tool()
async def tapcraft_list_schedules(workflow_id: int | None = None) -> str:
    """List cron schedules, optionally filtered by workflow.

    Args:
        workflow_id: Filter by workflow ID.
    """
    from src.services import crud

    db = await _get_db()
    try:
        schedules = await crud.list_schedules(db, WORKSPACE_ID, workflow_id=workflow_id)
        result = []
        for s in schedules:
            result.append(
                {
                    "id": s.id,
                    "workflow_id": s.workflow_id,
                    "name": s.name,
                    "cron": s.cron,
                    "timezone": s.timezone,
                    "enabled": s.enabled,
                    "next_run_at": _iso(s.next_run_at),
                    "last_run_at": _iso(s.last_run_at),
                    "created_at": _iso(s.created_at),
                }
            )
        return json.dumps(result, indent=2)
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_create_schedule(
    workflow_id: int,
    name: str,
    cron: str,
    timezone: str = "UTC",
    enabled: bool = True,
) -> str:
    """Create a cron schedule for a workflow.

    The schedule is registered in both the database and Temporal.

    Args:
        workflow_id: The workflow to schedule.
        name: Human-readable name for the schedule.
        cron: Standard 5-field cron expression (minute hour dom month dow)
              or a shorthand like @daily, @hourly.
        timezone: IANA timezone (default UTC).
        enabled: Whether the schedule is active immediately.
    """
    from src.services import crud
    from src.services.schedule_service import validate_cron, create_temporal_schedule

    db = await _get_db()
    try:
        if not validate_cron(cron):
            return json.dumps({"error": f"Invalid cron expression: '{cron}'"})

        wf = await crud.get_workflow(db, workflow_id)
        if not wf:
            return json.dumps({"error": f"Workflow {workflow_id} not found"})

        schedule = await crud.create_schedule(
            db,
            workspace_id=WORKSPACE_ID,
            workflow_id=workflow_id,
            name=name,
            cron=cron,
            timezone=timezone,
            enabled=enabled,
        )

        # Register in Temporal
        try:
            await create_temporal_schedule(
                schedule_id=schedule.id,
                workflow_entrypoint=wf.entrypoint_symbol,
                cron=cron,
                enabled=enabled,
            )
        except Exception as e:
            LOGGER.error("Failed to create Temporal schedule: %s", e)
            return json.dumps(
                {
                    "schedule_id": schedule.id,
                    "status": "created_in_db_only",
                    "warning": f"DB record created but Temporal schedule failed: {e}",
                }
            )

        return json.dumps(
            {
                "schedule_id": schedule.id,
                "workflow_id": workflow_id,
                "cron": cron,
                "enabled": enabled,
                "status": "created",
            }
        )
    finally:
        await db.close()


# ---- Repo sync ------------------------------------------------------------


@mcp.tool()
async def tapcraft_sync_repo() -> str:
    """Trigger git sync for the workspace.

    Pulls the latest code from the configured git repository and discovers
    new activities and workflows.
    """
    from src.services import crud
    from src.services.repo_sync import (
        clone_or_pull,
        discover_repo_activities,
        discover_repo_workflows,
    )

    db = await _get_db()
    try:
        workspace = await crud.get_workspace(db, WORKSPACE_ID)
        if not workspace:
            return json.dumps({"error": f"Workspace {WORKSPACE_ID} not found"})

        if not workspace.repo_url:
            return json.dumps({"error": "No repo_url configured for this workspace"})

        sync_status, sync_error = await clone_or_pull(workspace, db)

        discovered_activities = []
        discovered_workflows = []
        if sync_status == "synced":
            acts = discover_repo_activities(WORKSPACE_ID)
            discovered_activities = [getattr(a, "__name__", str(a)) for a in acts]
            wfs = discover_repo_workflows(WORKSPACE_ID)
            discovered_workflows = [getattr(w, "__name__", str(w)) for w in wfs]

        return json.dumps(
            {
                "sync_status": sync_status,
                "sync_error": sync_error,
                "discovered_activities": discovered_activities,
                "discovered_workflows": discovered_workflows,
            },
            indent=2,
        )
    finally:
        await db.close()


# ===== Webhook Tools =======================================================


@mcp.tool()
async def tapcraft_list_webhooks(workflow_id: int | None = None) -> str:
    """List all webhooks in the workspace, optionally filtered by workflow."""
    from src.services import crud

    db = await _get_db()
    try:
        webhooks = await crud.list_webhooks(db, workspace_id=WORKSPACE_ID, workflow_id=workflow_id)
        return json.dumps(
            [
                {
                    "id": w.id,
                    "workflow_id": w.workflow_id,
                    "path": w.path,
                    "enabled": w.enabled,
                    "trigger_count": w.trigger_count,
                    "last_triggered_at": w.last_triggered_at.isoformat()
                    if w.last_triggered_at
                    else None,
                }
                for w in webhooks
            ],
            indent=2,
        )
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_create_webhook(
    workflow_id: int,
    path: str,
    secret: str | None = None,
) -> str:
    """Create a webhook trigger for a workflow.

    Args:
        workflow_id: ID of the workflow to trigger
        path: URL path for the webhook (e.g. "my-webhook")
        secret: Optional HMAC secret for signature verification
    """
    from src.services import crud

    db = await _get_db()
    try:
        webhook = await crud.create_webhook(
            db,
            workspace_id=WORKSPACE_ID,
            workflow_id=workflow_id,
            path=path,
            secret=secret,
        )
        return json.dumps(
            {
                "id": webhook.id,
                "path": webhook.path,
                "url": f"POST /hooks/{webhook.path}",
                "enabled": webhook.enabled,
            },
            indent=2,
        )
    finally:
        await db.close()


@mcp.tool()
async def tapcraft_delete_webhook(webhook_id: int) -> str:
    """Delete a webhook by ID."""
    from src.services import crud

    db = await _get_db()
    try:
        deleted = await crud.delete_webhook(db, webhook_id)
        return json.dumps({"deleted": deleted})
    finally:
        await db.close()


# ===== MCP Resources =======================================================


@mcp.resource("tapcraft://docs/writing-workflows")
async def docs_writing_workflows() -> str:
    """How to write a Tapcraft workflow — Temporal patterns, constraints, and conventions."""
    return _DOC_WRITING_WORKFLOWS


@mcp.resource("tapcraft://docs/available-activities")
async def docs_available_activities() -> str:
    """Reference for all built-in activities with config schemas."""
    return _DOC_AVAILABLE_ACTIVITIES


@mcp.resource("tapcraft://docs/examples")
async def docs_examples() -> str:
    """Example workflows from the examples/ directory."""
    return _DOC_EXAMPLES


# ===== Documentation content ===============================================

_DOC_WRITING_WORKFLOWS = """\
# Writing Tapcraft Workflows

Tapcraft workflows are standard Temporal workflows written in Python.
They run on the Temporal worker and are deployed to the workspace directory.

## Basic structure

```python
from datetime import timedelta
from temporalio import workflow

@workflow.defn
class MyWorkflow:
    \"\"\"Description of what this workflow does.\"\"\"

    @workflow.run
    async def run(self, config: dict) -> dict:
        # 'config' is the input dict passed when starting the workflow.
        # Use workflow.execute_activity to call activities.

        result = await workflow.execute_activity(
            "net.http.request",            # activity name (string)
            {                               # config dict — single positional arg
                "method": "GET",
                "url": config.get("api_url", "https://example.com/data"),
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return {"status": "done", "result": result}
```

## Key rules

1. **No I/O in workflow code** — Temporal workflow code must be deterministic.
   All network calls, file operations, and side effects MUST go through activities.
   Never use `httpx`, `requests`, `open()`, `os.system()`, etc. directly in
   a `@workflow.defn` class.

2. **Use `workflow.execute_activity()`** to call activities:
   ```python
   result = await workflow.execute_activity(
       "activity.name",           # string name of the activity
       {"key": "value"},          # config dict (single argument)
       start_to_close_timeout=timedelta(minutes=5),
   )
   ```

3. **Always set `start_to_close_timeout`** — this is required by Temporal.
   Common values: `timedelta(seconds=30)` for fast ops, `timedelta(minutes=5)`
   for API calls, `timedelta(minutes=10)` for long-running activities.

4. **Use `workflow.sleep()` for delays**, not `asyncio.sleep()`:
   ```python
   await workflow.sleep(60)  # sleep 60 seconds
   ```

5. **Use `workflow.logger`** for logging, not the `logging` module:
   ```python
   workflow.logger.info(f"Processing {len(items)} items")
   ```

6. **The `run` method receives a `dict`** — convention is to name it `config`.
   Always use `.get()` with defaults for robustness:
   ```python
   url = config.get("api_url", "https://default.example.com")
   limit = config.get("limit", 25)
   ```

7. **Return a dict** from the `run` method summarizing results.

## Retry policies

```python
from temporalio.common import RetryPolicy

result = await workflow.execute_activity(
    "net.http.request",
    {"url": "https://api.example.com"},
    start_to_close_timeout=timedelta(minutes=5),
    retry_policy=RetryPolicy(
        maximum_attempts=3,
        initial_interval=timedelta(seconds=1),
        backoff_coefficient=2.0,
    ),
)
```

## Looping over items

```python
@workflow.run
async def run(self, config: dict) -> dict:
    urls = config.get("urls", [])
    results = []

    for url in urls:
        result = await workflow.execute_activity(
            "net.http.request",
            {"method": "GET", "url": url},
            start_to_close_timeout=timedelta(minutes=2),
        )
        results.append(result)

    return {"results": results, "count": len(results)}
```

## Chaining activities

```python
@workflow.run
async def run(self, config: dict) -> dict:
    # Step 1: Fetch RSS feed
    feed = await workflow.execute_activity(
        "feed.rss.read",
        {"url": config["feed_url"], "max_items": 10},
        start_to_close_timeout=timedelta(minutes=2),
    )

    # Step 2: Deduplicate by link
    deduped = await workflow.execute_activity(
        "data.dedup",
        {"items": feed["items"], "key_field": "link"},
        start_to_close_timeout=timedelta(minutes=1),
    )

    # Step 3: Post results
    result = await workflow.execute_activity(
        "net.http.request",
        {
            "method": "POST",
            "url": config["webhook_url"],
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(deduped["items"]),
        },
        start_to_close_timeout=timedelta(minutes=2),
    )

    return {"items_posted": deduped["count"], "http_status": result["status_code"]}
```

## Using secrets in activities

Secrets are stored encrypted and accessed at runtime in custom activities:

```python
from temporalio import activity
from src.services.secrets import get_secret

@activity.defn(name="my_custom.fetch_data")
async def fetch_data(config: dict) -> dict:
    api_key = await get_secret("MY_API_KEY")
    # Use api_key in your HTTP calls...
```

Workflows themselves should NOT access secrets directly — pass secret names
to activities that know how to resolve them.

## Writing custom activities

Custom activities go in the workspace's `activities/` directory:

```python
from temporalio import activity
from typing import Any, Dict

@activity.defn(name="myproject.fetch_data")
async def fetch_data(config: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"
    Fetch data from an API.

    Args:
        config: Dict containing:
            - api_url: The URL to fetch from
            - api_key_secret: Name of the secret holding the API key

    Returns:
        Dict with 'data' key containing the fetched data.
    \"\"\"
    import httpx
    from src.services.secrets import get_secret

    url = config.get("api_url", "")
    secret_name = config.get("api_key_secret", "")

    api_key = await get_secret(secret_name) if secret_name else ""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return {"data": response.json()}
```

Key rules for activities:
- Decorate with `@activity.defn(name="unique.activity.name")`
- Accept a single `config: Dict[str, Any]` parameter
- Return a `Dict[str, Any]`
- Activities CAN do I/O (HTTP, file, database, etc.)
- Use `httpx` for HTTP calls (async)
- Handle errors gracefully and return error info in the result dict

## Deploying via MCP

Use `tapcraft_deploy_workflow` to deploy:
1. Write your complete Python module code
2. Pass it to `tapcraft_deploy_workflow` with a slug and name
3. Use `tapcraft_run_workflow` to execute it

The deploy tool writes the code to the workspace and registers it in the database.
The Temporal worker picks it up automatically.
"""

_DOC_AVAILABLE_ACTIVITIES = """\
# Built-in Activities Reference

These activities are available on every Tapcraft installation.
Call them from workflows using `workflow.execute_activity("name", config_dict, ...)`.

---

## net.http.request

Execute a single HTTP request.

**Config:**
| Key     | Type   | Required | Default | Description              |
|---------|--------|----------|---------|--------------------------|
| method  | string | no       | GET     | HTTP method              |
| url     | string | yes      |         | Target URL               |
| headers | object | no       | {}      | HTTP headers             |
| body    | any    | no       |         | Request body             |

**Returns:** `{status_code, body, headers}`

**Example:**
```python
result = await workflow.execute_activity(
    "net.http.request",
    {"method": "POST", "url": "https://api.example.com/data", "headers": {"Authorization": "Bearer xyz"}},
    start_to_close_timeout=timedelta(minutes=5),
)
```

---

## net.http.parallel

Run multiple HTTP requests in parallel using asyncio.gather.

**Config:**
| Key      | Type  | Required | Default | Description                              |
|----------|-------|----------|---------|------------------------------------------|
| requests | array | yes      |         | List of request dicts (method, url, etc) |
| timeout  | float | no       | 30      | Per-request timeout in seconds           |

Each request dict in the array has the same shape as `net.http.request` config,
plus an optional `label` field.

**Returns:** `{results: [{label, status_code, body, headers, error}], count}`

**Example:**
```python
result = await workflow.execute_activity(
    "net.http.parallel",
    {
        "requests": [
            {"url": "https://api1.example.com", "label": "api1"},
            {"url": "https://api2.example.com", "label": "api2"},
        ],
        "timeout": 15,
    },
    start_to_close_timeout=timedelta(minutes=2),
)
```

---

## feed.rss.read

Fetch and parse an RSS or Atom feed.

**Config:**
| Key       | Type    | Required | Default | Description              |
|-----------|---------|----------|---------|--------------------------|
| url       | string  | yes      |         | Feed URL                 |
| max_items | integer | no       | 20      | Maximum items to return  |

**Returns:** `{items: [{title, link, published, summary, author}], count}`

**Example:**
```python
result = await workflow.execute_activity(
    "feed.rss.read",
    {"url": "https://news.ycombinator.com/rss", "max_items": 10},
    start_to_close_timeout=timedelta(minutes=2),
)
```

---

## data.parse_xml

Parse an XML string into a nested dict representation.

**Config:**
| Key        | Type   | Required | Description          |
|------------|--------|----------|----------------------|
| xml_string | string | yes      | Raw XML to parse     |

**Returns:** `{result: {tag, attrib, text, children}}`

---

## data.dedup

Deduplicate a list of dicts by a specified key field.

**Config:**
| Key       | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| items     | array  | yes      | List of dicts to deduplicate   |
| key_field | string | yes      | Dict key for uniqueness check  |

**Returns:** `{items, count, duplicates_removed}`

**Example:**
```python
result = await workflow.execute_activity(
    "data.dedup",
    {"items": all_stories, "key_field": "url"},
    start_to_close_timeout=timedelta(minutes=1),
)
```

---

## files.read

Read a file from the workspace filesystem.

**Config:**
| Key  | Type   | Required | Description   |
|------|--------|----------|---------------|
| path | string | yes      | File path     |

**Returns:** `{content, path}` or `{error}`

---

## files.write

Write content to a file in the workspace.

**Config:**
| Key     | Type   | Required | Description      |
|---------|--------|----------|------------------|
| path    | string | yes      | File path        |
| content | string | yes      | Content to write |

**Returns:** `{success, path}` or `{error}`
"""

_DOC_EXAMPLES = """\
# Example Workflows

These examples are from the `examples/gtm-dashboard/` directory and demonstrate
real-world Tapcraft workflow patterns.

---

## 1. Daily Metrics Pull (simplest)

A minimal workflow that calls a single HTTP activity.

```python
from datetime import timedelta
from temporalio import workflow

@workflow.defn
class DailyMetricsWorkflow:
    \"\"\"Pull daily metrics on a schedule.\"\"\"

    @workflow.run
    async def run(self, config: dict) -> dict:
        api_base_url = config.get("api_base_url", "http://localhost:8000")

        result = await workflow.execute_activity(
            "net.http.request",
            {
                "method": "POST",
                "url": f"{api_base_url}/api/metrics/pull",
                "headers": {"Content-Type": "application/json"},
            },
            start_to_close_timeout=timedelta(minutes=5),
        )
        return result
```

---

## 2. Reddit Monitor (loop + chain)

Fetches posts from multiple subreddits, transforms them, and ingests as signals.
Demonstrates looping over a list and chaining activities.

```python
from datetime import timedelta
from temporalio import workflow

DEFAULT_SUBREDDITS = ["machinelearning", "artificial", "LocalLLaMA", "startups"]

@workflow.defn
class RedditMonitorWorkflow:
    \"\"\"Fetch Reddit posts and ingest as signals.\"\"\"

    @workflow.run
    async def run(self, config: dict) -> dict:
        subreddits = config.get("subreddits", DEFAULT_SUBREDDITS)
        limit = config.get("limit", 25)
        api_base_url = config.get("api_base_url", "http://localhost:8000")

        all_posts = []
        fetch_results = {}

        # Loop: Fetch from each subreddit
        for subreddit in subreddits:
            result = await workflow.execute_activity(
                "reddit.fetch_posts",
                {"subreddit": subreddit, "limit": limit},
                start_to_close_timeout=timedelta(minutes=2),
            )
            posts = result.get("posts", [])
            all_posts.extend(posts)
            fetch_results[subreddit] = len(posts)

        if not all_posts:
            return {"status": "complete", "total_fetched": 0}

        # Transform + Ingest (chained activities)
        transform_result = await workflow.execute_activity(
            "data.transform",
            {"input_data": all_posts, "code": "...transform code..."},
            start_to_close_timeout=timedelta(minutes=2),
        )

        ingest_result = await workflow.execute_activity(
            "signals.ingest",
            {"signals": transform_result.get("result", []), "api_base_url": api_base_url},
            start_to_close_timeout=timedelta(minutes=3),
        )

        return {
            "status": "complete",
            "total_fetched": len(all_posts),
            "total_ingested": ingest_result.get("ingested", 0),
            "by_subreddit": fetch_results,
        }
```

---

## 3. HN Monitor (search + dedup + transform + ingest)

Demonstrates searching, deduplication, and multi-step data pipelines.

```python
from datetime import timedelta
from temporalio import workflow

DEFAULT_QUERIES = ["AI agent", "LLM", "automation", "developer tools"]

@workflow.defn
class HackerNewsMonitorWorkflow:
    \"\"\"Search HN and ingest as signals.\"\"\"

    @workflow.run
    async def run(self, config: dict) -> dict:
        queries = config.get("queries", DEFAULT_QUERIES)
        hours_back = config.get("hours_back", 24)

        all_stories = []
        for query in queries:
            result = await workflow.execute_activity(
                "hackernews.search",
                {"query": query, "tags": "story", "hours_back": hours_back},
                start_to_close_timeout=timedelta(minutes=2),
            )
            all_stories.extend(result.get("hits", []))

        if not all_stories:
            return {"status": "complete", "total_fetched": 0}

        # Dedup by URL
        dedup_result = await workflow.execute_activity(
            "data.dedup",
            {"items": all_stories, "key_field": "url"},
            start_to_close_timeout=timedelta(minutes=1),
        )
        unique = dedup_result.get("items", all_stories)

        return {
            "status": "complete",
            "total_fetched": len(all_stories),
            "unique_count": len(unique),
        }
```

---

## 4. Custom Activity Example

How to write a custom activity for use in workflows:

```python
# activities/my_api.py
from temporalio import activity
from typing import Any, Dict
import httpx

@activity.defn(name="myapi.fetch_users")
async def fetch_users(config: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Fetch users from an API.\"\"\"
    url = config.get("url", "https://api.example.com/users")
    limit = config.get("limit", 50)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{url}?limit={limit}", timeout=30.0)
        response.raise_for_status()
        users = response.json()

    return {"users": users, "count": len(users)}
```

Then in a workflow:
```python
result = await workflow.execute_activity(
    "myapi.fetch_users",
    {"url": "https://api.example.com/users", "limit": 100},
    start_to_close_timeout=timedelta(minutes=2),
)
```
"""


# ===== Entry point =========================================================


def main():
    """Run the Tapcraft MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
