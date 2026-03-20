"""Resolve Temporal workflow classes from entrypoint strings.

Handles both dotted paths ('module.path.ClassName') and bare class names
('ClassName'). For bare names, searches sys.modules for already-loaded
workflow classes (works because the worker imports all workflow modules at startup).
"""

import importlib
import inspect
import sys


def resolve_workflow_class(entrypoint: str):
    """Resolve a workflow class from either a dotted path or bare class name."""
    if "." in entrypoint:
        module_path, class_name = entrypoint.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    # Bare class name — search loaded modules for a Temporal workflow class
    for mod in sys.modules.values():
        try:
            cls = getattr(mod, entrypoint, None)
            if cls is not None and inspect.isclass(cls) and hasattr(cls, "__temporal_workflow_definition"):
                return cls
        except Exception:
            continue

    raise ValueError(f"Cannot resolve workflow class '{entrypoint}' — not found in loaded modules")
