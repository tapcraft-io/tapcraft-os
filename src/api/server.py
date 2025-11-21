"""FastAPI application exposing core Tapcraft OS endpoints."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.models.core import (
    AgentGeneration,
    AgentManifest,
    AgentPrompt,
    Capability,
    Issue,
    PlanDoc,
)
from src.services.agent_service import AgentService
from src.services.capabilities_service import CapabilitiesService
from src.services.memory_service import MemoryService
from src.services.template_service import TemplateService
from src.services.validation_service import ValidationService

# Import database initialization
from src.db.base import init_db

# Import routers
from src.api.routers import apps, workflows, graphs, schedules, runs

app = FastAPI(title="Tapcraft OS API", version="0.1.0")

# Register routers
app.include_router(apps.router)
app.include_router(workflows.router)
app.include_router(graphs.router)
app.include_router(schedules.router)
app.include_router(runs.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()


DEFAULT_CAPABILITIES = [
    Capability(
        id="net.http.request",
        params_schema={
            "type": "object",
            "properties": {
                "method": {"type": "string"},
                "url": {"type": "string"},
                "headers": {"type": "object"},
                "body": {"type": "string"},
            },
        },
        returns_schema={"type": "object", "properties": {"status_code": {"type": "integer"}}},
    ),
    Capability(id="files.read", params_schema={"type": "object", "properties": {"path": {"type": "string"}}}),
    Capability(
        id="files.write",
        params_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        },
    ),
    Capability(
        id="git.commit_and_push",
        params_schema={
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}},
                "message": {"type": "string"},
            },
        },
    ),
    Capability(
        id="mcp.call",
        params_schema={
            "type": "object",
            "properties": {"tool_id": {"type": "string"}, "params": {"type": "object"}},
        },
    ),
]

capabilities_service = CapabilitiesService(DEFAULT_CAPABILITIES)
validation_service = ValidationService()
memory_service = MemoryService()
template_service = TemplateService()
agent_service = AgentService(capabilities_service, validation_service, memory_service, template_service)


class RuntimeConfig:
    def __init__(self) -> None:
        self.timezone = os.getenv("TZ_DEFAULT", "UTC")
        self.task_queue = os.getenv("TASK_QUEUE", "default")

    def model_dump(self) -> Dict[str, str]:
        return {"timezone": self.timezone, "task_queue": self.task_queue}

    def update(self, payload: Dict[str, str]) -> None:
        if "timezone" in payload:
            self.timezone = payload["timezone"]
        if "task_queue" in payload:
            self.task_queue = payload["task_queue"]


class AgentPromptPayload(BaseModel):
    task_text: str
    capabilities: Optional[List[Capability]] = None
    constraints: List[str] = Field(default_factory=list)
    defaults: Dict[str, Any] = Field(default_factory=dict)

    def to_agent_prompt(self) -> AgentPrompt:
        caps = self.capabilities or capabilities_service.list_capabilities()
        return AgentPrompt(
            task_text=self.task_text,
            capabilities=caps,
            constraints=self.constraints,
            defaults=self.defaults,
        )


class PlanResponse(BaseModel):
    plan: PlanDoc
    required_tools: List[str]


class ValidationResponse(BaseModel):
    ok: bool
    issues: List[Issue]
    diagnostics: Dict[str, Any]


class RepairRequest(BaseModel):
    module_text: str
    issues: List[Issue] = Field(default_factory=list)
    last_error_log: Optional[str] = None


class RepairResponse(BaseModel):
    patched_module_text: str
    notes: str


class TestsRequest(BaseModel):
    module_text: str
    manifest: AgentManifest


class MemoryUpdateRequest(BaseModel):
    summary: str
    prompts: Dict[str, Any] = Field(default_factory=dict)
    tool_choices: List[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def get_config() -> RuntimeConfig:
    return RuntimeConfig()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def read_config() -> Dict[str, str]:
    return get_config().model_dump()


@app.put("/config")
def update_config(payload: Dict[str, str]) -> Dict[str, str]:
    config = get_config()
    config.update(payload)
    return config.model_dump()


@app.get("/config/capabilities")
def list_capabilities() -> Dict[str, List[Capability]]:
    return {"capabilities": capabilities_service.list_capabilities()}


@app.post("/config/capabilities/refresh")
def refresh_capabilities() -> Dict[str, List[Capability]]:
    return {"capabilities": capabilities_service.refresh()}


@app.get("/config/capabilities/schema/{tool_id}")
def get_capability_schema(tool_id: str) -> Dict[str, Any]:
    schema = capabilities_service.get_schema(tool_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Capability not found")
    return schema


@app.post("/agent/plan", response_model=PlanResponse)
def agent_plan(payload: AgentPromptPayload) -> PlanResponse:
    plan, tools = agent_service.plan(payload.to_agent_prompt())
    return PlanResponse(plan=plan, required_tools=tools)


class GenerateRequest(BaseModel):
    prompt: AgentPromptPayload
    plan: PlanDoc


@app.post("/agent/generate", response_model=AgentGeneration)
def agent_generate(payload: GenerateRequest) -> AgentGeneration:
    prompt = payload.prompt.to_agent_prompt()
    return agent_service.generate(prompt, payload.plan)


class ValidateRequest(BaseModel):
    module_text: str


@app.post("/agent/validate", response_model=ValidationResponse)
def agent_validate(payload: ValidateRequest) -> ValidationResponse:
    result = agent_service.validate(payload.module_text)
    return ValidationResponse(ok=result.ok, issues=result.issues, diagnostics=result.diagnostics.model_dump())


@app.post("/agent/repair", response_model=RepairResponse)
def agent_repair(payload: RepairRequest) -> RepairResponse:
    response = agent_service.repair(payload.module_text, payload.issues, payload.last_error_log)
    return RepairResponse(**response)


@app.post("/agent/tests")
def agent_tests(payload: TestsRequest) -> Dict[str, Any]:
    generation = AgentGeneration(module_text=payload.module_text, manifest=payload.manifest)
    tests = agent_service.generate_tests(generation)
    return tests.model_dump()


@app.get("/agent/templates")
def agent_templates() -> Dict[str, Any]:
    return {"task_types": agent_service.template_task_types(), "templates": agent_service.list_templates()}


@app.get("/agent/models")
def agent_models() -> Dict[str, Dict[str, str]]:
    return {"models": agent_service.models_matrix()}


@app.put("/agent/models")
def agent_update_models(payload: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    models = agent_service.update_models(payload)
    return {"models": models}


@app.get("/agent/limits")
def agent_limits() -> Dict[str, Any]:
    limits = agent_service.limits()
    return {
        "max_tokens_plan": limits.max_tokens_plan,
        "max_tokens_gen": limits.max_tokens_gen,
        "max_tokens_repair": limits.max_tokens_repair,
        "max_tokens_tests": limits.max_tokens_tests,
        "rate_limit_rpm": limits.rate_limit_rpm,
    }


@app.put("/agent/limits")
def agent_update_limits(payload: Dict[str, int]) -> Dict[str, Any]:
    limits = agent_service.update_limits(payload)
    return {
        "max_tokens_plan": limits.max_tokens_plan,
        "max_tokens_gen": limits.max_tokens_gen,
        "max_tokens_repair": limits.max_tokens_repair,
        "max_tokens_tests": limits.max_tokens_tests,
        "rate_limit_rpm": limits.rate_limit_rpm,
    }


@app.get("/agent/memory/{workflow_ref}")
def agent_memory(workflow_ref: str) -> Dict[str, Any]:
    return agent_service.get_memory(workflow_ref)


@app.post("/agent/memory/{workflow_ref}")
def agent_memory_update(workflow_ref: str, payload: MemoryUpdateRequest) -> Dict[str, Any]:
    return agent_service.store_memory(workflow_ref, payload.summary, payload.prompts, payload.tool_choices)


@app.get("/runs/{run_id}/error")
def runs_error(run_id: str) -> Dict[str, Any]:
    return {
        "short_summary": f"No additional error information available for run {run_id}",
        "failing_activity": None,
        "stack_excerpt": "",
    }
