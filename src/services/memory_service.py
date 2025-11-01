"""Simple filesystem backed memory store for agent decisions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic.json import pydantic_encoder

from src.models.core import DecisionRecord


class MemoryService:
    """Persists agent memories to disk for later retrieval."""

    def __init__(self, base_path: str | Path = "data/memory") -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def append_decision(self, record: DecisionRecord) -> None:
        payload = self._read_payload(record.workflow_ref)
        decisions: List[Dict[str, Any]] = payload.setdefault("decisions", [])
        decisions.append(json.loads(json.dumps(record.model_dump(), default=pydantic_encoder)))
        payload["versions"] = len(decisions)
        self._write_payload(record.workflow_ref, payload)

    def list_decisions(self, workflow_ref: str) -> List[DecisionRecord]:
        payload = self._read_payload(workflow_ref)
        raw = payload.get("decisions", [])
        return [DecisionRecord(**item) for item in raw]

    def update_memory(self, workflow_ref: str, summary: str, prompts: Dict[str, Any], tool_choices: List[str]) -> None:
        payload = self._read_payload(workflow_ref)
        payload["summary"] = summary
        payload["prompts"] = prompts
        payload["tool_choices"] = tool_choices
        self._write_payload(workflow_ref, payload)

    def get_memory(self, workflow_ref: str) -> Dict[str, Any]:
        payload = self._read_payload(workflow_ref)
        payload.setdefault("decisions", [])
        payload.setdefault("prompts", {})
        payload.setdefault("tool_choices", [])
        payload.setdefault("summary", "")
        payload.setdefault("versions", len(payload.get("decisions", [])))
        return payload

    def _workflow_file(self, workflow_ref: str) -> Path:
        safe_ref = workflow_ref.replace("/", "_")
        return self._base_path / f"{safe_ref}.json"

    def _read_payload(self, workflow_ref: str) -> Dict[str, Any]:
        file_path = self._workflow_file(workflow_ref)
        if not file_path.exists():
            return {}
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_payload(self, workflow_ref: str, payload: Dict[str, Any]) -> None:
        file_path = self._workflow_file(workflow_ref)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=pydantic_encoder)
