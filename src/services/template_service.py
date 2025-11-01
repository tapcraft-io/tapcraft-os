"""Utility helpers for loading agent prompt templates."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List


class TemplateService:
    """Loads plan and generation prompt templates from disk."""

    def __init__(self, templates_path: str | Path = "src/agent/templates") -> None:
        self._templates_path = Path(templates_path)

    def list_templates(self) -> Dict[str, str]:
        templates: Dict[str, str] = {}
        if not self._templates_path.exists():
            return templates
        for path in sorted(self._templates_path.glob("*.txt")):
            templates[path.stem] = path.read_text(encoding="utf-8")
        return templates

    def task_types(self) -> List[str]:
        return sorted(self.list_templates().keys())
