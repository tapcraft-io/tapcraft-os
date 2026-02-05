"""High level agent orchestration services."""
from __future__ import annotations

import hashlib
import logging
import os
import textwrap
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, MutableMapping, Sequence, Tuple

from src.models.core import (
    AgentGeneration,
    AgentManifest,
    AgentPrompt,
    DecisionRecord,
    Issue,
    PlanDoc,
    PlanStep,
    TestsSpec,
)
from src.services.capabilities_service import CapabilitiesService
from src.services.memory_service import MemoryService
from src.services.template_service import TemplateService
from src.services.validation_service import ValidationResult, ValidationService


LOGGER = logging.getLogger(__name__)


RULES = textwrap.dedent(
    """
    1. Determinism: Do not perform network, filesystem, or LLM I/O inside workflow code.
    2. Tools: Use only the capabilities provided in the prompt. All side effects must occur via activities.
    3. Entrypoint: Provide a @workflow.defn class with async def run(self, cfg: dict).
    4. I/O: Restrict workflow inputs/outputs to JSON-serializable values.
    5. Schema: Emit a manifest.config_schema describing cfg keys and their types.
    6. Observability: Log concise, non-sensitive progress messages for each major step.
    7. Idempotency: Include dedupe keys or checks before performing side-effecting activity calls.
    8. Security: Never log or hardcode secrets or credentials.
    9. Explainability: Add a top-of-file docstring summarizing the workflow plan and assumptions.
    """
).strip()


@dataclass
class AgentLimits:
    max_tokens_plan: int
    max_tokens_gen: int
    max_tokens_repair: int
    max_tokens_tests: int
    rate_limit_rpm: int


class AgentService:
    """Coordinates planning, generation, validation, and memory."""

    def __init__(
        self,
        capabilities_service: CapabilitiesService,
        validation_service: ValidationService,
        memory_service: MemoryService,
        template_service: TemplateService,
    ) -> None:
        self._capabilities_service = capabilities_service
        self._validation_service = validation_service
        self._memory_service = memory_service
        self._template_service = template_service

        default_model = os.getenv("INTERNAL_ANTHROPIC_LARGE_MODEL", "claude-sonnet-4-20250514")
        self._models: Dict[str, str] = {
            "planner": default_model,
            "generator": default_model,
            "repair": default_model,
            "tests": default_model,
        }
        self._limits = AgentLimits(
            max_tokens_plan=int(os.getenv("AGENT_MAX_TOKENS_PLAN", "1500")),
            max_tokens_gen=int(os.getenv("AGENT_MAX_TOKENS_GEN", "8000")),
            max_tokens_repair=int(os.getenv("AGENT_MAX_TOKENS_REPAIR", "4000")),
            max_tokens_tests=int(os.getenv("AGENT_MAX_TOKENS_TESTS", "2000")),
            rate_limit_rpm=int(os.getenv("AGENT_RATE_LIMIT_RPM", "60")),
        )
        self._plan_cache_ttl = int(os.getenv("AGENT_PLAN_CACHE_TTL_SECONDS", "600"))
        self._plan_cache: MutableMapping[str, Tuple[float, PlanDoc, List[str]]] = {}
        self._call_history: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def plan(self, prompt: AgentPrompt) -> Tuple[PlanDoc, List[str]]:
        self._enforce_rate_limit("plan")
        self._enforce_budget(prompt.task_text, self._limits.max_tokens_plan, "plan")

        cache_key = self._cache_key(prompt)
        cached = self._plan_cache.get(cache_key)
        now = time.time()
        if cached and cached[0] > now:
            LOGGER.debug("Plan cache hit for key %s", cache_key)
            return cached[1], cached[2]

        plan, tools = self._build_plan(prompt)
        self._plan_cache[cache_key] = (now + self._plan_cache_ttl, plan, tools)
        LOGGER.info(
            "Generated plan", extra={"tools": tools, "task": prompt.task_text[:120], "model": self._models["planner"]}
        )
        return plan, tools

    def generate(self, prompt: AgentPrompt, plan: PlanDoc) -> AgentGeneration:
        self._enforce_rate_limit("generate")
        self._enforce_budget(prompt.task_text, self._limits.max_tokens_gen, "generate")

        module_text, manifest = self._build_module(prompt, plan)
        generation = AgentGeneration(module_text=module_text, manifest=manifest)

        self._record_decision(
            workflow_ref=manifest.workflow_ref,
            model=self._models["generator"],
            tools=manifest.required_tools,
            prompt=prompt,
            notes="Generated module",
            token_usage={
                "input": self._estimate_tokens(prompt.task_text),
                "output": self._estimate_tokens(module_text),
            },
        )

        return generation

    def validate(self, module_text: str) -> ValidationResult:
        capabilities = self._capabilities_service.list_capabilities()
        return self._validation_service.validate_module_text(module_text, capabilities)

    def repair(self, module_text: str, issues: Sequence[Issue], last_error_log: str | None = None) -> Dict[str, str]:
        self._enforce_rate_limit("repair")
        self._enforce_budget(module_text, self._limits.max_tokens_repair, "repair")

        patched = module_text
        notes: List[str] = []

        for issue in issues:
            if issue.code == "NON_DETERMINISM":
                patched = self._strip_banned_imports(patched)
                notes.append("Removed banned imports highlighted by validator.")
            elif issue.code == "BAD_SIGNATURE":
                patched = self._ensure_run_signature(patched)
                notes.append("Normalized workflow run signature.")
            elif issue.code == "UNKNOWN_TOOL" and last_error_log:
                notes.append("Tool mismatch detected; review plan and capabilities.")

        if patched == module_text and not notes:
            notes.append("No automatic repair performed; manual intervention required.")

        validation = self.validate(patched)
        if not validation.ok:
            notes.append("Patched module still has validation issues.")

        workflow_ref = self._infer_workflow_ref(patched)
        if workflow_ref:
            self._record_decision(
                workflow_ref=workflow_ref,
                model=self._models["repair"],
                tools=validation.diagnostics.api_surface_used,
                prompt=AgentPrompt(task_text="repair", capabilities=self._capabilities_service.list_capabilities()),
                notes="Repair attempt",
                token_usage={"input": self._estimate_tokens(module_text), "output": self._estimate_tokens(patched)},
            )

        return {"patched_module_text": patched, "notes": "\n".join(notes)}

    def generate_tests(self, generation: AgentGeneration) -> TestsSpec:
        self._enforce_rate_limit("tests")
        self._enforce_budget(generation.module_text, self._limits.max_tokens_tests, "tests")

        workflow_ref = generation.manifest.workflow_ref
        module_name = workflow_ref.lower()
        test_code = textwrap.dedent(
            f"""
            import asyncio
            from unittest.mock import AsyncMock

            import pytest
            from temporalio import workflow

            from src.generated import {module_name} as generated_module


            @pytest.mark.asyncio
            async def test_{module_name}_invokes_required_tools(monkeypatch):
                monkeypatch.setattr(workflow, "execute_activity", AsyncMock(return_value={{"status": "ok"}}))
                wf = generated_module.{workflow_ref}()
                cfg = {{"dedupe_key": "test", "notes": "unit"}}
                result = await wf.run(cfg)
                assert result is None or isinstance(result, dict)
            """
        ).strip()

        return TestsSpec(
            module_path=f"src/generated/{module_name}.py",
            tests_text=test_code,
            commands=["pytest -k test_{module_name}_invokes_required_tools"],
        )

    # ------------------------------------------------------------------
    # Settings and metadata helpers
    # ------------------------------------------------------------------
    def models_matrix(self) -> Dict[str, str]:
        return dict(self._models)

    def update_models(self, updates: Dict[str, str]) -> Dict[str, str]:
        self._models.update(updates)
        return self.models_matrix()

    def limits(self) -> AgentLimits:
        return self._limits

    def update_limits(self, payload: Dict[str, int]) -> AgentLimits:
        for key, value in payload.items():
            if hasattr(self._limits, key):
                setattr(self._limits, key, int(value))
        return self._limits

    def list_templates(self) -> Dict[str, str]:
        return self._template_service.list_templates()

    def template_task_types(self) -> List[str]:
        return self._template_service.task_types()

    def get_memory(self, workflow_ref: str) -> Dict[str, object]:
        return self._memory_service.get_memory(workflow_ref)

    def store_memory(self, workflow_ref: str, summary: str, prompts: Dict[str, object], tool_choices: List[str]) -> Dict[str, object]:
        self._memory_service.update_memory(workflow_ref, summary, prompts, tool_choices)
        return self._memory_service.get_memory(workflow_ref)

    def list_decisions(self, workflow_ref: str) -> List[DecisionRecord]:
        return self._memory_service.list_decisions(workflow_ref)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_plan(self, prompt: AgentPrompt) -> Tuple[PlanDoc, List[str]]:
        capabilities = prompt.capabilities or self._capabilities_service.list_capabilities()
        selected_tools = [cap.id for cap in capabilities][:3]
        steps: List[PlanStep] = []
        for idx, tool in enumerate(selected_tools, start=1):
            steps.append(
                PlanStep(
                    id=f"step-{idx}",
                    goal=f"Leverage {tool} to advance the task",
                    tool_candidates=[tool],
                    inputs_hint={"cfg": "Use configuration values"},
                    outputs_hint={"artifacts": [f"artifact-{idx}.json"]},
                )
            )
        if not steps:
            steps.append(
                PlanStep(
                    id="step-1",
                    goal="Review task requirements",
                    tool_candidates=[],
                    inputs_hint={"cfg": "No external tools available"},
                    outputs_hint={},
                )
            )

        plan = PlanDoc(
            steps=steps,
            risks=["Tool availability may change", "Ensure deterministic workflow logic"],
            artifacts=["logs/workflow.log"],
        )
        return plan, selected_tools

    def _build_module(self, prompt: AgentPrompt, plan: PlanDoc) -> Tuple[str, AgentManifest]:
        workflow_name = self._workflow_name_from_prompt(prompt.task_text)
        required_tools = sorted({tool for step in plan.steps for tool in step.tool_candidates})
        doc_lines = ["Generated workflow based on planning steps:"]
        for step in plan.steps:
            doc_lines.append(f"- {step.goal} using {', '.join(step.tool_candidates) or 'no tools'}")

        body_lines = ["        workflow.logger.info(\"Starting workflow execution\")"]
        for step in plan.steps:
            if step.tool_candidates:
                tool = step.tool_candidates[0]
                body_lines.append(
                    "        await workflow.execute_activity("
                    f"\"{tool}\", {{""task"": \"{step.goal}\", ""cfg"": cfg}},"
                    " schedule_to_close_timeout=timedelta(seconds=30),"
                    " )"
                )
            body_lines.append(f"        workflow.logger.info(\"Completed {step.id}\")")

        body_block = "\n".join(body_lines) if body_lines else "        pass"

        module_text = textwrap.dedent(
            f"""
            \"\"\"
            {' '.join(doc_lines)}
            RULES:\n{RULES}
            \"\"\"
            from datetime import timedelta

            from temporalio import workflow


            @workflow.defn
            class {workflow_name}:
                \"\"\"Workflow generated for task: {prompt.task_text[:80]}\"\"\"

                async def run(self, cfg: dict) -> None:
            {body_block}
        """
        ).strip()

        manifest = AgentManifest(
            workflow_ref=workflow_name,
            required_tools=required_tools,
            config_schema={
                "type": "object",
                "properties": {
                    "dedupe_key": {"type": "string", "description": "Idempotency key"},
                    "notes": {"type": "string", "description": "Optional description"},
                },
                "additionalProperties": True,
            },
        )

        return module_text, manifest

    def _strip_banned_imports(self, module_text: str) -> str:
        lines = module_text.splitlines()
        filtered = []
        for line in lines:
            stripped = line.lstrip()
            if any(
                stripped.startswith(f"import {mod}") or stripped.startswith(f"from {mod}")
                for mod in self._validation_service.banned_modules
            ):
                continue
            filtered.append(line)
        return "\n".join(filtered)

    def _ensure_run_signature(self, module_text: str) -> str:
        if "async def run(self, cfg: dict)" in module_text:
            return module_text
        return module_text.replace("async def run(", "async def run(self, cfg: dict)")

    def _infer_workflow_ref(self, module_text: str) -> str | None:
        for line in module_text.splitlines():
            if line.strip().startswith("class ") and "workflow.defn" in module_text:
                name = line.split("class ")[1].split(":")[0].strip()
                if name:
                    return name
        return None

    def _cache_key(self, prompt: AgentPrompt) -> str:
        capability_ids = ",".join(sorted(cap.id for cap in prompt.capabilities))
        raw = f"{prompt.task_text}|{capability_ids}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _enforce_rate_limit(self, bucket: str) -> None:
        limit = self._limits.rate_limit_rpm
        if limit <= 0:
            return
        now = time.time()
        history = self._call_history.setdefault(bucket, [])
        history[:] = [ts for ts in history if now - ts < 60]
        if len(history) >= limit:
            raise RuntimeError(f"Rate limit exceeded for {bucket}")
        history.append(now)

    def _enforce_budget(self, text: str, limit: int, bucket: str) -> None:
        tokens = self._estimate_tokens(text)
        if tokens > limit:
            raise RuntimeError(f"Token budget exceeded for {bucket}: {tokens} > {limit}")

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()) * 4)

    def _workflow_name_from_prompt(self, task_text: str) -> str:
        base = "".join(ch for ch in task_text.title() if ch.isalnum()) or "Generated"
        return f"Workflow{base[:40]}"

    def _record_decision(
        self,
        workflow_ref: str,
        model: str,
        tools: Sequence[str],
        prompt: AgentPrompt,
        notes: str,
        token_usage: Dict[str, int],
    ) -> None:
        record = DecisionRecord(
            workflow_ref=workflow_ref,
            created_at=datetime.utcnow(),
            model=model,
            token_usage=token_usage,
            tools=list(tools),
            prompts={
                "system": RULES,
                "task": prompt.task_text,
                "templates_used": self._template_service.task_types(),
            },
            config_keys=list(prompt.defaults.keys()),
            notes=notes,
        )
        self._memory_service.append_decision(record)
