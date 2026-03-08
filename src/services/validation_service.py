"""Static validation utilities for generated workflow modules."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from src.models.core import Capability, Issue, ValidationDiag


_TOOL_STRING = re.compile(r"^[a-zA-Z0-9_.-]+$")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: List[Issue]
    diagnostics: ValidationDiag


class ValidationService:
    """Validates generated workflow modules against determinism rules."""

    def __init__(self, banned_modules: Iterable[str] | None = None) -> None:
        default_banned = {
            "httpx",
            "requests",
            "os",
            "subprocess",
            "pathlib",
            "openai",
            "asyncio",
        }
        if banned_modules is not None:
            default_banned.update(banned_modules)
        self._banned_modules = default_banned

    @property
    def banned_modules(self) -> set[str]:
        return set(self._banned_modules)

    def validate_module_text(
        self, module_text: str, capabilities: Sequence[Capability]
    ) -> ValidationResult:
        issues: List[Issue] = []
        diagnostics = ValidationDiag()

        try:
            tree = ast.parse(module_text)
        except SyntaxError as exc:  # pragma: no cover - defensive
            issues.append(
                Issue(
                    code="SYNTAX_ERROR",
                    message=f"Syntax error: {exc.msg}",
                    location={"line": exc.lineno, "offset": exc.offset},
                )
            )
            return ValidationResult(False, issues, diagnostics)

        available_tools = {cap.id for cap in capabilities}

        banned_hits: List[str] = []
        workflow_class_found = False
        async_run_found = False
        discovered_tools: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = self._import_name(node)
                if module_name and module_name.split(".")[0] in self._banned_modules:
                    banned_hits.append(module_name)
            if isinstance(node, ast.ClassDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute) and decorator.attr == "defn":
                        workflow_class_found = True
                for body_item in node.body:
                    if isinstance(body_item, ast.AsyncFunctionDef) and body_item.name == "run":
                        async_run_found = self._validate_run_signature(body_item, issues)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                candidate = node.value.strip()
                if candidate in available_tools and candidate not in discovered_tools:
                    discovered_tools.append(candidate)
                elif "." in candidate and _TOOL_STRING.match(candidate):
                    if (
                        candidate not in available_tools
                        and candidate not in diagnostics.unknown_tools
                    ):
                        diagnostics.unknown_tools.append(candidate)

        if banned_hits:
            diagnostics.banned_imports.extend(sorted(set(banned_hits)))
            issues.append(
                Issue(
                    code="NON_DETERMINISM",
                    message="Banned modules imported: " + ", ".join(sorted(set(banned_hits))),
                    fix_hint="Move side effects to activities and remove the imports from the workflow.",
                )
            )

        if not workflow_class_found:
            issues.append(
                Issue(
                    code="WORKFLOW_MISSING",
                    message="Expected a @workflow.defn class definition but none were found.",
                    fix_hint="Define a workflow class decorated with @workflow.defn.",
                )
            )

        if not async_run_found:
            issues.append(
                Issue(
                    code="BAD_SIGNATURE",
                    message="Workflow must define async def run(self, cfg: dict).",
                    fix_hint="Ensure the workflow class implements async def run(self, cfg: dict).",
                )
            )

        diagnostics.api_surface_used.extend(discovered_tools)

        ok = not issues and not diagnostics.unknown_tools
        if diagnostics.unknown_tools:
            issues.append(
                Issue(
                    code="UNKNOWN_TOOL",
                    message="Module references tools that are not registered.",
                    fix_hint="Update the plan to use existing capabilities or register new tools.",
                )
            )

        return ValidationResult(ok, issues, diagnostics)

    def _import_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.ImportFrom):
            return node.module or None
        if isinstance(node, ast.Import):
            if node.names:
                return node.names[0].name
        return None

    def _validate_run_signature(self, func: ast.AsyncFunctionDef, issues: List[Issue]) -> bool:
        if not func.args.args:
            issues.append(
                Issue(
                    code="BAD_SIGNATURE",
                    message="run method must accept self and cfg arguments.",
                )
            )
            return False
        if len(func.args.args) < 2:
            issues.append(
                Issue(
                    code="BAD_SIGNATURE",
                    message="run method must accept cfg argument.",
                )
            )
            return False
        cfg_arg = func.args.args[1]
        if cfg_arg.annotation and not (
            isinstance(cfg_arg.annotation, ast.Name) and cfg_arg.annotation.id == "dict"
        ):
            issues.append(
                Issue(
                    code="BAD_SIGNATURE",
                    message="cfg parameter must be annotated as dict.",
                )
            )
        return True
