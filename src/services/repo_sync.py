"""Git-based project sync service.

Clones or pulls a git repo into a workspace directory,
then discovers @activity.defn functions and @workflow.defn classes.
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from urllib.parse import urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession
from temporalio import activity, workflow

from src.db.models import Workspace

LOGGER = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent / "workspace"


def get_repo_path(workspace_id: int) -> Path:
    """Return the repo checkout path for a workspace."""
    return WORKSPACE_ROOT / f"workspace_{workspace_id}" / "repo"


def _inject_auth_into_url(repo_url: str, token: str) -> str:
    """Embed a PAT into an HTTPS git URL for auth."""
    parsed = urlparse(repo_url)
    if parsed.scheme not in ("https", "http"):
        return repo_url
    authed = parsed._replace(netloc=f"x-access-token:{token}@{parsed.hostname}")
    return urlunparse(authed)


def _ensure_init_files(repo_path: Path) -> None:
    """Ensure __init__.py exists at key directories for Python module resolution."""
    for subdir in [repo_path, repo_path / "activities", repo_path / "workflows"]:
        if subdir.is_dir():
            init_file = subdir / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")
                LOGGER.debug(f"Created {init_file}")


async def clone_or_pull(workspace: Workspace, db: AsyncSession) -> Tuple[str, Optional[str]]:
    """Clone or pull a repo for the given workspace.

    Returns:
        (sync_status, sync_error) tuple
    """
    if not workspace.repo_url:
        return ("error", "No repo_url configured")

    repo_path = get_repo_path(workspace.id)
    branch = workspace.repo_branch or "main"

    # Resolve auth token if configured
    clone_url = workspace.repo_url
    if workspace.repo_auth_secret:
        try:
            from src.services.secrets import get_secret
            token = await get_secret(workspace.repo_auth_secret)
            clone_url = _inject_auth_into_url(workspace.repo_url, token)
        except Exception as e:
            LOGGER.error(f"Failed to resolve repo auth secret: {e}")
            return ("error", f"Auth secret error: {e}")

    # Update workspace status
    workspace.sync_status = "syncing"
    await db.commit()

    try:
        if (repo_path / ".git").is_dir():
            # Pull
            LOGGER.info(f"Pulling repo for workspace {workspace.id} at {repo_path}")
            proc = await asyncio.create_subprocess_exec(
                "git", "pull", "--ff-only",
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode().strip()
                LOGGER.error(f"git pull failed: {err}")
                return ("error", f"git pull failed: {err}")
        else:
            # Shallow clone
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            LOGGER.info(
                f"Cloning {workspace.repo_url} (branch={branch}) "
                f"into {repo_path}"
            )
            proc = await asyncio.create_subprocess_exec(
                "git", "clone",
                "--depth", "1",
                "--branch", branch,
                clone_url,
                str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode().strip()
                LOGGER.error(f"git clone failed: {err}")
                return ("error", f"git clone failed: {err}")

        _ensure_init_files(repo_path)

        workspace.last_synced_at = datetime.utcnow()
        workspace.sync_status = "synced"
        workspace.sync_error = None
        await db.commit()
        return ("synced", None)

    except Exception as e:
        LOGGER.exception(f"Repo sync failed for workspace {workspace.id}")
        workspace.sync_status = "error"
        workspace.sync_error = str(e)
        await db.commit()
        return ("error", str(e))


def discover_repo_activities(workspace_id: int) -> List[Callable[..., Any]]:
    """Discover @activity.defn functions from a workspace's cloned repo."""
    activities: List[Callable[..., Any]] = []
    repo_path = get_repo_path(workspace_id)
    activities_dir = repo_path / "activities"

    if not activities_dir.is_dir():
        return activities

    for py_file in activities_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        try:
            module_name = (
                f"workspace.workspace_{workspace_id}.repo.activities.{py_file.stem}"
            )
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if not (spec and spec.loader):
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            for attr_name, obj in inspect.getmembers(module):
                if callable(obj) and hasattr(obj, "__temporal_activity_definition"):
                    activities.append(obj)
                    LOGGER.info(
                        f"Discovered activity: {attr_name} from {module_name}"
                    )
        except Exception as e:
            LOGGER.error(f"Failed to load activities from {py_file}: {e}")

    return activities


def discover_repo_workflows(workspace_id: int) -> List[Type]:
    """Discover @workflow.defn classes from a workspace's cloned repo."""
    workflows: List[Type] = []
    repo_path = get_repo_path(workspace_id)
    workflows_dir = repo_path / "workflows"

    if not workflows_dir.is_dir():
        return workflows

    for py_file in workflows_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        try:
            module_name = (
                f"workspace.workspace_{workspace_id}.repo.workflows.{py_file.stem}"
            )
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if not (spec and spec.loader):
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            for attr_name, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "__temporal_workflow_definition"):
                    workflows.append(obj)
                    LOGGER.info(
                        f"Discovered workflow: {attr_name} from {module_name}"
                    )
        except Exception as e:
            LOGGER.error(f"Failed to load workflows from {py_file}: {e}")

    return workflows
