"""Temporal worker entrypoint with dynamic workflow and activity loading."""
from __future__ import annotations

import asyncio
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Type

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

# Add workspace directory to Python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent / "workspace"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

LOGGER = logging.getLogger(__name__)

GENERATED_PATH = Path(__file__).resolve().parent.parent / "generated"

TASK_QUEUE = os.getenv("TASK_QUEUE", "default")
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")


def discover_workflows_from_generated() -> List[Type[workflow.Workflow]]:
    """Discover workflows from src/generated directory (legacy)."""
    workflows: List[Type[workflow.Workflow]] = []

    if not GENERATED_PATH.exists():
        return workflows

    for module_path in GENERATED_PATH.glob("*.py"):
        spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "_workflow_run_fn"):
                    workflows.append(obj)

    return workflows


def discover_workflows_from_workspace() -> List[Type[workflow.Workflow]]:
    """Discover workflows from workspace directories."""
    workflows: List[Type[workflow.Workflow]] = []

    if not WORKSPACE_ROOT.exists():
        LOGGER.warning(f"Workspace root does not exist: {WORKSPACE_ROOT}")
        return workflows

    # Scan all workspace_* directories
    for workspace_dir in WORKSPACE_ROOT.glob("workspace_*"):
        workflows_dir = workspace_dir / "workflows"
        if not workflows_dir.exists():
            continue

        # Import workflows from this workspace
        for workflow_file in workflows_dir.glob("*.py"):
            if workflow_file.name == "__init__.py":
                continue

            try:
                # Build module name: workspace.workspace_N.workflows.module_name
                workspace_id = workspace_dir.name
                module_name = workflow_file.stem
                full_module_name = f"workspace.{workspace_id}.workflows.{module_name}"

                # Import the module
                spec = importlib.util.spec_from_file_location(
                    full_module_name, workflow_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[full_module_name] = module
                    spec.loader.exec_module(module)

                    # Find workflow classes
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if hasattr(obj, "_workflow_run_fn"):
                            workflows.append(obj)
                            LOGGER.info(
                                f"Discovered workflow: {obj.__name__} from {full_module_name}"
                            )

            except Exception as e:
                LOGGER.error(f"Failed to load workflow from {workflow_file}: {e}")

    return workflows


async def load_app_operations_from_db() -> List[Dict[str, Any]]:
    """Load app operations from database."""
    try:
        from src.db.base import AsyncSessionLocal
        from src.services import crud

        async with AsyncSessionLocal() as db:
            # Get all workspaces
            workspaces = await crud.list_workspaces(db)

            all_operations = []
            for workspace in workspaces:
                # Get all apps in workspace
                apps = await crud.list_apps(db, workspace_id=workspace.id)
                for app in apps:
                    for op in app.operations:
                        all_operations.append(
                            {
                                "code_symbol": op.code_symbol,
                                "name": op.name,
                                "display_name": op.display_name,
                            }
                        )

            LOGGER.info(f"Loaded {len(all_operations)} app operations from database")
            return all_operations

    except Exception as e:
        LOGGER.error(f"Failed to load app operations from database: {e}")
        return []


# Built-in activities (legacy placeholders)
@activity.defn(name="net.http.request.legacy")
async def net_http_request(_: Dict[str, Any]) -> Dict[str, Any]:
    LOGGER.info("net.http.request placeholder invoked")
    return {"status": "ok"}


@activity.defn(name="files.read.legacy")
async def files_read(_: Dict[str, Any]) -> str:
    LOGGER.info("files.read placeholder invoked")
    return ""


@activity.defn(name="files.write.legacy")
async def files_write(_: Dict[str, Any]) -> Dict[str, Any]:
    LOGGER.info("files.write placeholder invoked")
    return {"status": "ok"}


@activity.defn(name="git.commit_and_push")
async def git_commit_and_push(_: Dict[str, Any]) -> Dict[str, Any]:
    LOGGER.info("git.commit_and_push placeholder invoked")
    return {"status": "ok"}


@activity.defn(name="mcp.call")
async def mcp_call(_: Dict[str, Any]) -> Dict[str, Any]:
    LOGGER.info("mcp.call placeholder invoked")
    return {"status": "ok"}


def built_in_activities() -> Iterable[Callable[..., Any]]:
    return [
        net_http_request,
        files_read,
        files_write,
        git_commit_and_push,
        mcp_call,
    ]


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Connect to Temporal
    client = await Client.connect(TEMPORAL_ADDRESS)

    # Discover workflows from both legacy and workspace directories
    workflows_generated = discover_workflows_from_generated()
    workflows_workspace = discover_workflows_from_workspace()
    all_workflows = workflows_generated + workflows_workspace

    LOGGER.info(
        f"Discovered {len(workflows_generated)} workflows from generated/, "
        f"{len(workflows_workspace)} from workspace/"
    )

    # Load app operations from database and register activities
    from src.services.activity_registry import ActivityRegistry

    activity_registry = ActivityRegistry()

    app_operations = await load_app_operations_from_db()
    activity_registry.load_app_operations_from_db(app_operations)

    # Get all activities (built-in + registered)
    all_activities = list(built_in_activities()) + activity_registry.get_all_activities()

    LOGGER.info(
        f"Registering {len(all_workflows)} workflows and {len(all_activities)} activities"
    )

    # Start worker
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=all_workflows,
        activities=all_activities,
    ):
        LOGGER.info(f"Worker started on task queue '{TASK_QUEUE}'")
        LOGGER.info(f"Watching workspace directory: {WORKSPACE_ROOT}")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
