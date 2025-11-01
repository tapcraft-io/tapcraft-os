"""Temporal service client abstraction."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio import schedule
from temporalio.client import Client, ScheduleHandle

from src.models.core import ScheduleSpec


@dataclass
class TemporalConfig:
    address: str
    task_queue: str


class TemporalService:
    """High-level helper around the Temporal Python SDK."""

    def __init__(self, config: TemporalConfig) -> None:
        self._config = config
        self._client: Optional[Client] = None

    async def get_client(self) -> Client:
        if self._client is None:
            self._client = await Client.connect(self._config.address)
        return self._client

    async def start_workflow(self, workflow_ref: str, args: Dict[str, Any]) -> str:
        client = await self.get_client()
        handle = await client.start_workflow(
            workflow=workflow_ref,
            id=f"{workflow_ref}-{int(time.time()*1000)}",
            task_queue=self._config.task_queue,
            input=args,
        )
        return handle.id

    async def create_schedule(self, spec: ScheduleSpec) -> ScheduleHandle:
        client = await self.get_client()
        schedule_spec = schedule.Schedule(
            action=schedule.ScheduleActionStartWorkflow(
                workflow=spec.workflow_ref,
                task_queue=self._config.task_queue,
                args=[spec.args],
            ),
            spec=schedule.ScheduleSpec(cron_expressions=[spec.cron], timezone=spec.timezone),
        )
        return await client.create_schedule(spec.name, schedule_spec)

    async def get_schedule(self, name: str) -> ScheduleHandle:
        client = await self.get_client()
        return client.get_schedule_handle(name)

    async def list_schedules(self) -> List[schedule.ScheduleListDescription]:
        client = await self.get_client()
        descriptions: List[schedule.ScheduleListDescription] = []
        async for desc in client.list_schedules():
            descriptions.append(desc)
        return descriptions

    async def update_schedule(self, name: str, patch: Dict[str, Any]) -> None:
        handle = await self.get_schedule(name)

        def updater(input_: schedule.ScheduleUpdateInput) -> schedule.Schedule:
            current = input_.description.schedule
            action = current.action
            if isinstance(action, schedule.ScheduleActionStartWorkflow):
                args = action.args[0] if action.args else {}
            else:
                args = {}

            cron = patch.get("cron") or current.spec.cron_expressions[0]
            timezone = patch.get("timezone") or current.spec.timezone
            if "args" in patch:
                args = patch["args"]

            if isinstance(action, schedule.ScheduleActionStartWorkflow):
                action = schedule.ScheduleActionStartWorkflow(
                    workflow=action.workflow,
                    task_queue=action.task_queue,
                    args=[args],
                )

            state = current.state or schedule.ScheduleState()
            if patch.get("status") == "paused":
                state = schedule.ScheduleState(paused=True)
            elif patch.get("status") == "running":
                state = schedule.ScheduleState(paused=False)

            return schedule.Schedule(
                action=action,
                spec=schedule.ScheduleSpec(cron_expressions=[cron], timezone=timezone),
                policies=current.policies,
                state=state,
            )

        await handle.update(updater)

    async def delete_schedule(self, name: str) -> None:
        handle = await self.get_schedule(name)
        await handle.delete()


def build_temporal_service_from_env() -> TemporalService:
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    task_queue = os.getenv("TASK_QUEUE", "default")
    return TemporalService(TemporalConfig(address=address, task_queue=task_queue))
