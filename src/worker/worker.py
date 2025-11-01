"""Temporal worker entrypoint."""
from __future__ import annotations

import asyncio
import importlib.util
import inspect
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Type

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

LOGGER = logging.getLogger(__name__)

GENERATED_PATH = Path(__file__).resolve().parent.parent / "generated"

TASK_QUEUE = os.getenv('TASK_QUEUE', 'default')
TEMPORAL_ADDRESS = os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')


def discover_workflows() -> List[Type[workflow.Workflow]]:
    workflows: List[Type[workflow.Workflow]] = []
    for module_path in GENERATED_PATH.glob("*.py"):
        spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, '_workflow_run_fn'):
                    workflows.append(obj)
    return workflows


@activity.defn
async def net_http_request(_: Dict[str, Any]) -> Dict[str, Any]:
    LOGGER.info("net.http.request placeholder invoked")
    return {"status": "ok"}


@activity.defn
async def files_read(_: Dict[str, Any]) -> str:
    LOGGER.info("files.read placeholder invoked")
    return ""


@activity.defn
async def files_write(_: Dict[str, Any]) -> Dict[str, Any]:
    LOGGER.info("files.write placeholder invoked")
    return {"status": "ok"}


@activity.defn
async def git_commit_and_push(_: Dict[str, Any]) -> Dict[str, Any]:
    LOGGER.info("git.commit_and_push placeholder invoked")
    return {"status": "ok"}


@activity.defn
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
    client = await Client.connect(TEMPORAL_ADDRESS)
    workflows = discover_workflows()
    LOGGER.info("Registering %s workflows", len(workflows))
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=workflows,
        activities=list(built_in_activities()),
    ):
        LOGGER.info("Worker started on task queue '%s'", TASK_QUEUE)
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
