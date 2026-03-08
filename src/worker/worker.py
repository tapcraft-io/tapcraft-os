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

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from src.activities import (
    # Platform: Generic Data Activities
    http_parallel,
    rss_read,
    parse_xml,
    dedup,
)

# Add workspace directory to Python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent / "workspace"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

LOGGER = logging.getLogger(__name__)

GENERATED_PATH = Path(__file__).resolve().parent.parent / "generated"

TASK_QUEUE = os.getenv("TASK_QUEUE", "default")
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

_SKIP_DIRS = frozenset((".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"))


def add_repo_dirs_to_sys_path() -> None:
    """Add each workspace repo directory to sys.path for cross-module imports.

    This allows workflow code that lives in a subdirectory (e.g. repo/tapcraft/)
    to import sibling packages (e.g. ``from tapcraft.activities.foo import Bar``).
    """
    if not WORKSPACE_ROOT.exists():
        return
    for workspace_dir in WORKSPACE_ROOT.glob("workspace_*"):
        repo_dir = workspace_dir / "repo"
        if repo_dir.is_dir() and str(repo_dir) not in sys.path:
            sys.path.insert(0, str(repo_dir))
            LOGGER.info(f"Added {repo_dir} to sys.path")


def _collect_search_dirs(workspace_dir: Path, kind: str) -> List[Path]:
    """Return all directories that may contain workflow or activity .py files.

    Checks:
      - workspace_dir/{kind}/
      - workspace_dir/repo/{kind}/
      - workspace_dir/repo/<subdir>/{kind}/   (one level deep, for monorepo layouts)
    """
    dirs: List[Path] = [
        workspace_dir / kind,
        workspace_dir / "repo" / kind,
    ]
    repo_dir = workspace_dir / "repo"
    if repo_dir.is_dir():
        for child in repo_dir.iterdir():
            if child.is_dir() and child.name not in _SKIP_DIRS:
                candidate = child / kind
                if candidate.is_dir():
                    dirs.append(candidate)
    return dirs


def discover_workflows_from_generated() -> List[Type[Any]]:
    """Discover workflows from src/generated directory (legacy)."""
    workflows: List[Type[Any]] = []

    if not GENERATED_PATH.exists():
        return workflows

    for module_path in GENERATED_PATH.glob("*.py"):
        spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "__temporal_workflow_definition"):
                    workflows.append(obj)

    return workflows


def discover_workflows_from_workspace() -> List[Type[Any]]:
    """Discover workflows from workspace directories (generated + repo)."""
    workflows: List[Type[Any]] = []

    if not WORKSPACE_ROOT.exists():
        LOGGER.warning(f"Workspace root does not exist: {WORKSPACE_ROOT}")
        return workflows

    # Scan all workspace_* directories
    for workspace_dir in WORKSPACE_ROOT.glob("workspace_*"):
        search_dirs = _collect_search_dirs(workspace_dir, "workflows")

        for workflows_dir in search_dirs:
            if not workflows_dir.exists():
                continue

            for workflow_file in workflows_dir.glob("*.py"):
                if workflow_file.name == "__init__.py":
                    continue

                try:
                    workspace_id = workspace_dir.name
                    module_name = workflow_file.stem
                    # Build module name based on path
                    rel = workflows_dir.relative_to(workspace_dir)
                    parts = [workspace_id] + list(rel.parts) + [module_name]
                    full_module_name = f"workspace.{'.'.join(parts)}"

                    spec = importlib.util.spec_from_file_location(full_module_name, workflow_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[full_module_name] = module
                        spec.loader.exec_module(module)

                        for _, obj in inspect.getmembers(module, inspect.isclass):
                            if hasattr(obj, "__temporal_workflow_definition"):
                                workflows.append(obj)
                                LOGGER.info(
                                    f"Discovered workflow: {obj.__name__} from {full_module_name}"
                                )

                except Exception as e:
                    LOGGER.error(f"Failed to load workflow from {workflow_file}: {e}")

    return workflows


def discover_activities_from_workspace() -> List[Callable[..., Any]]:
    """Discover @activity.defn functions from workspace directories (repo/activities/)."""
    activities: List[Callable[..., Any]] = []

    if not WORKSPACE_ROOT.exists():
        return activities

    for workspace_dir in WORKSPACE_ROOT.glob("workspace_*"):
        search_dirs = _collect_search_dirs(workspace_dir, "activities")

        for activities_dir in search_dirs:
            if not activities_dir.is_dir():
                continue

            for py_file in activities_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue

                try:
                    workspace_id = workspace_dir.name
                    rel = activities_dir.relative_to(workspace_dir)
                    parts = [workspace_id] + list(rel.parts) + [py_file.stem]
                    full_module_name = f"workspace.{'.'.join(parts)}"

                    spec = importlib.util.spec_from_file_location(full_module_name, py_file)
                    if not (spec and spec.loader):
                        continue

                    module = importlib.util.module_from_spec(spec)
                    sys.modules[full_module_name] = module
                    spec.loader.exec_module(module)

                    for attr_name, obj in inspect.getmembers(module):
                        if callable(obj) and hasattr(obj, "__temporal_activity_definition"):
                            activities.append(obj)
                            LOGGER.info(f"Discovered activity: {attr_name} from {full_module_name}")

                except Exception as e:
                    LOGGER.error(f"Failed to load activities from {py_file}: {e}")

    return activities


async def load_activity_operations_from_db() -> List[Dict[str, Any]]:
    """Load activity operations from database."""
    try:
        from src.db.base import AsyncSessionLocal
        from src.services import crud

        async with AsyncSessionLocal() as db:
            # Get all workspaces
            workspaces = await crud.list_workspaces(db)

            all_operations = []
            for workspace in workspaces:
                # Get all activities in workspace
                activities = await crud.list_activities(db, workspace_id=workspace.id)
                for act in activities:
                    for op in act.operations:
                        all_operations.append(
                            {
                                "code_symbol": op.code_symbol,
                                "name": op.name,
                                "display_name": op.display_name,
                            }
                        )

            LOGGER.info(f"Loaded {len(all_operations)} activity operations from database")
            return all_operations

    except Exception as e:
        LOGGER.error(f"Failed to load activity operations from database: {e}")
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


def built_in_activities() -> Iterable[Callable[..., Any]]:
    return [
        net_http_request,
        files_read,
        files_write,
        git_commit_and_push,
        # Platform: Generic Data Activities
        http_parallel,
        rss_read,
        parse_xml,
        dedup,
    ]


RELOAD_CHECK_INTERVAL = int(os.getenv("WORKER_RELOAD_CHECK_INTERVAL", "5"))


def snapshot_workspace_files() -> set[str]:
    """Return a set of activity/workflow .py file paths in the workspace."""
    files: set[str] = set()
    if not WORKSPACE_ROOT.exists():
        return files
    for workspace_dir in WORKSPACE_ROOT.glob("workspace_*"):
        for kind in ("workflows", "activities"):
            for search_dir in _collect_search_dirs(workspace_dir, kind):
                if search_dir.exists():
                    for f in search_dir.glob("*.py"):
                        if f.name != "__init__.py":
                            files.add(str(f))
    if GENERATED_PATH.exists():
        for f in GENERATED_PATH.glob("*.py"):
            files.add(str(f))
    return files


async def watch_for_new_workflows(known_files: set[str], shutdown_event: asyncio.Event) -> None:
    """Poll workspace for new workflow/activity files; signal shutdown when found."""
    while not shutdown_event.is_set():
        await asyncio.sleep(RELOAD_CHECK_INTERVAL)
        current = snapshot_workspace_files()
        new_files = current - known_files
        if new_files:
            LOGGER.info(
                f"Detected {len(new_files)} new file(s): "
                f"{[Path(f).name for f in new_files]} — restarting worker to register them"
            )
            shutdown_event.set()
            return


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Connect to Temporal
    client = await Client.connect(TEMPORAL_ADDRESS)

    # Add repo directories to sys.path so cross-module imports work
    # (e.g. workflow code importing from sibling activity packages)
    add_repo_dirs_to_sys_path()

    # Discover workflows from legacy generated/ and workspace directories (including repos)
    workflows_generated = discover_workflows_from_generated()
    workflows_workspace = discover_workflows_from_workspace()
    all_workflows = workflows_generated + workflows_workspace

    LOGGER.info(
        f"Discovered {len(workflows_generated)} from generated/, "
        f"{len(workflows_workspace)} from workspace/"
    )

    # Discover activities from workspace repos
    workspace_activities = discover_activities_from_workspace()
    LOGGER.info(f"Discovered {len(workspace_activities)} activities from workspace repos")

    # Load activity operations from database and register activities
    from src.services.activity_registry import ActivityRegistry

    activity_registry = ActivityRegistry()

    activity_operations = await load_activity_operations_from_db()
    activity_registry.load_activity_operations_from_db(activity_operations)

    # Get all activities (built-in + workspace-discovered + registry)
    all_activities = (
        list(built_in_activities()) + workspace_activities + activity_registry.get_all_activities()
    )

    LOGGER.info(f"Registering {len(all_workflows)} workflows and {len(all_activities)} activities")

    # Reconcile DB schedules with Temporal on startup
    try:
        from src.services.schedule_service import reconcile_schedules_from_db

        reconciled = await reconcile_schedules_from_db()
        LOGGER.info("Schedule reconciliation complete (%d created)", reconciled)
    except Exception as e:
        LOGGER.error("Schedule reconciliation failed: %s", e)

    # Snapshot current files so we can detect new ones
    known_files = snapshot_workspace_files()
    shutdown_event = asyncio.Event()

    # Start worker
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=all_workflows,
        activities=all_activities,
    ):
        LOGGER.info(f"Worker started on task queue '{TASK_QUEUE}'")
        LOGGER.info(f"Registered workflows: {[w.__name__ for w in all_workflows]}")
        LOGGER.info(f"Watching workspace for new files (every {RELOAD_CHECK_INTERVAL}s)")

        # Run file watcher alongside the worker
        watcher = asyncio.create_task(watch_for_new_workflows(known_files, shutdown_event))
        await shutdown_event.wait()
        watcher.cancel()

    LOGGER.info("Worker shutting down for reload — Docker will restart it")


if __name__ == "__main__":
    asyncio.run(main())
