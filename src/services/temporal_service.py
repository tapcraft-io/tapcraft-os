"""Temporal service client abstraction."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleHandle,
    ScheduleListDescription,
    ScheduleSpec as TemporalScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
    ScheduleUpdateInput,
)

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
            workflow_ref,
            arg=args,
            id=f"{workflow_ref}-{int(time.time()*1000)}",
            task_queue=self._config.task_queue,
        )
        return handle.id

    async def create_schedule(self, spec: ScheduleSpec) -> ScheduleHandle:
        client = await self.get_client()
        temporal_schedule = Schedule(
            action=ScheduleActionStartWorkflow(
                spec.workflow_ref,
                args=[spec.args],
                id=f"scheduled-{spec.name}-{{{{.ScheduledTime}}}}",
                task_queue=self._config.task_queue,
            ),
            spec=TemporalScheduleSpec(cron_expressions=[spec.cron], time_zone_name=spec.timezone),
        )
        return await client.create_schedule(spec.name, temporal_schedule)

    async def get_schedule(self, name: str) -> ScheduleHandle:
        client = await self.get_client()
        return client.get_schedule_handle(name)

    async def list_schedules(self) -> List[ScheduleListDescription]:
        client = await self.get_client()
        descriptions: List[ScheduleListDescription] = []
        async for desc in await client.list_schedules():
            descriptions.append(desc)
        return descriptions

    async def update_schedule(self, name: str, patch: Dict[str, Any]) -> None:
        handle = await self.get_schedule(name)

        def updater(input_: ScheduleUpdateInput) -> ScheduleUpdate:
            current = input_.description.schedule
            action = current.action
            if isinstance(action, ScheduleActionStartWorkflow):
                args = action.args[0] if action.args else {}
            else:
                args = {}

            cron = patch.get("cron") or current.spec.cron_expressions[0]
            time_zone = patch.get("timezone") or current.spec.time_zone_name
            if "args" in patch:
                args = patch["args"]

            if isinstance(action, ScheduleActionStartWorkflow):
                action = ScheduleActionStartWorkflow(
                    action.workflow,
                    args=[args],
                    id=action.id,
                    task_queue=action.task_queue,
                )

            state = current.state or ScheduleState()
            if patch.get("status") == "paused":
                state = ScheduleState(paused=True)
            elif patch.get("status") == "running":
                state = ScheduleState(paused=False)

            updated = Schedule(
                action=action,
                spec=TemporalScheduleSpec(cron_expressions=[cron], time_zone_name=time_zone),
                policy=current.policy,
                state=state,
            )
            return ScheduleUpdate(schedule=updated)

        await handle.update(updater)

    async def delete_schedule(self, name: str) -> None:
        handle = await self.get_schedule(name)
        await handle.delete()


def build_temporal_service_from_env() -> TemporalService:
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    task_queue = os.getenv("TASK_QUEUE", "default")
    return TemporalService(TemporalConfig(address=address, task_queue=task_queue))
