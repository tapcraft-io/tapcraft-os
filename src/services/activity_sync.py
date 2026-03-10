"""Sync discovered activity functions into the Tapcraft database.

When the worker discovers ``@activity.defn`` functions from workspace code
and built-in modules, this service creates corresponding Activity and
ActivityOperation records in the database so the UI can display them.

Activities are grouped by source module — one Activity per module file,
with one Operation per ``@activity.defn`` function in that module.

The sync is idempotent: re-running it skips activities that already exist
(matched by slug).
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Callable, Dict, List, Set

from src.db.base import AsyncSessionLocal
from src.services import crud

LOGGER = logging.getLogger(__name__)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    """Convert a name into a URL-safe slug."""
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\\1", name)
    s = s.lower().strip()
    s = _NON_ALNUM.sub("-", s)
    return s.strip("-")


def _humanize(name: str) -> str:
    """Convert a snake_case or slug name into a human-readable title.

    Example: ``signal_pipeline`` -> ``Signal Pipeline``
    """
    s = name.replace("_", " ").replace("-", " ")
    return s.title()


def _get_activity_name(fn: Callable[..., Any]) -> str:
    """Extract the Temporal activity name from a decorated function."""
    defn = getattr(fn, "__temporal_activity_definition", None)
    if defn and hasattr(defn, "name") and defn.name:
        return defn.name
    return getattr(fn, "__name__", "unknown")


def _get_module_name(fn: Callable[..., Any]) -> str:
    """Extract the module name from a function."""
    return getattr(fn, "__module__", "") or "unknown"


def _group_by_module(
    activities: List[Callable[..., Any]],
) -> Dict[str, List[Callable[..., Any]]]:
    """Group activity functions by their source module."""
    groups: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
    for fn in activities:
        module = _get_module_name(fn)
        groups[module].append(fn)
    return dict(groups)


async def sync_activities_to_db(
    workspace_id: int,
    workspace_activities: List[Callable[..., Any]],
    builtin_activities: List[Callable[..., Any]],
) -> Dict[str, int]:
    """Sync discovered activity functions into the database.

    Groups functions by module, creates an Activity record per module,
    and an ActivityOperation record per function.

    Args:
        workspace_id: The target workspace.
        workspace_activities: Activities discovered from workspace code.
        builtin_activities: Built-in platform activities.

    Returns:
        A dict with ``activities_created``, ``operations_created``, and
        ``skipped`` counts.
    """
    stats = {"activities_created": 0, "operations_created": 0, "skipped": 0}

    all_fns = builtin_activities + workspace_activities
    if not all_fns:
        return stats

    grouped = _group_by_module(all_fns)

    async with AsyncSessionLocal() as db:
        # Load existing activities for dedup
        existing = await crud.list_activities(db=db, workspace_id=workspace_id)
        existing_slugs: Set[str] = {a.slug for a in existing}

        # Also build a set of existing operation code_symbols across all activities
        existing_symbols: Set[str] = set()
        for act in existing:
            for op in act.operations:
                existing_symbols.add(op.code_symbol)

        for module_path, fns in grouped.items():
            # Derive a readable name from the module path
            # e.g. "workspace.workspace_1.repo.tapcraft.activities.signal_pipeline"
            #   -> "signal_pipeline" -> "Signal Pipeline"
            module_leaf = module_path.rsplit(".", 1)[-1]
            slug = _slugify(module_leaf)
            display_name = _humanize(module_leaf)

            if slug in existing_slugs:
                # Activity exists — but check for new operations
                act = next(a for a in existing if a.slug == slug)
                for fn in fns:
                    symbol = _get_activity_name(fn)
                    if symbol in existing_symbols:
                        stats["skipped"] += 1
                        continue

                    fn_name = getattr(fn, "__name__", symbol)
                    try:
                        await crud.create_activity_operation(
                            db=db,
                            activity_id=act.id,
                            name=fn_name,
                            display_name=_humanize(fn_name),
                            code_symbol=symbol,
                            description=getattr(fn, "__doc__", None) or "",
                        )
                        stats["operations_created"] += 1
                        existing_symbols.add(symbol)
                    except Exception as exc:
                        LOGGER.warning("Failed to create operation %s: %s", symbol, exc)
                continue

            # Create new Activity
            try:
                activity = await crud.create_activity(
                    db=db,
                    workspace_id=workspace_id,
                    name=display_name,
                    slug=slug,
                    code_module_path=module_path,
                    description=f"Activities from {module_path}",
                    category=_categorize_module(module_path),
                )
                existing_slugs.add(slug)
                stats["activities_created"] += 1

                # Create operations for each function
                for fn in fns:
                    symbol = _get_activity_name(fn)
                    fn_name = getattr(fn, "__name__", symbol)
                    try:
                        await crud.create_activity_operation(
                            db=db,
                            activity_id=activity.id,
                            name=fn_name,
                            display_name=_humanize(fn_name),
                            code_symbol=symbol,
                            description=getattr(fn, "__doc__", None) or "",
                        )
                        stats["operations_created"] += 1
                        existing_symbols.add(symbol)
                    except Exception as exc:
                        LOGGER.warning("Failed to create operation %s: %s", symbol, exc)

                LOGGER.info(
                    "Synced activity '%s' (%d operations) from %s",
                    display_name,
                    len(fns),
                    module_path,
                )

            except Exception as exc:
                LOGGER.warning(
                    "Failed to create activity for module %s: %s",
                    module_path,
                    exc,
                )

    LOGGER.info(
        "Activity sync complete: %d activities created, %d operations created, %d skipped",
        stats["activities_created"],
        stats["operations_created"],
        stats["skipped"],
    )
    return stats


def _categorize_module(module_path: str) -> str:
    """Assign a category based on the module path."""
    lower = module_path.lower()
    if "builtin" in lower or module_path.startswith("src."):
        return "platform"
    return "workspace"
