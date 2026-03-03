"""Deduplication activity for Temporal workflows."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from temporalio import activity

LOGGER = logging.getLogger(__name__)


@activity.defn(name="data.dedup")
async def dedup(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deduplicate a list of dicts by a specified key field.

    First-occurrence order is preserved.  Items missing the key field are
    kept (they cannot be compared for duplicates).

    Args:
        config: Dict containing:
            - items: List of dicts to deduplicate.
            - key_field: The dict key used to determine uniqueness.

    Returns:
        dict with ``items`` (deduplicated list), ``count`` (items after dedup),
        and ``duplicates_removed`` (number of items dropped).
    """
    items: List[Dict[str, Any]] = config.get("items", [])
    key_field: str = config.get("key_field", "")

    if not key_field:
        return {
            "items": items,
            "count": len(items),
            "duplicates_removed": 0,
            "error": "No key_field provided; returning items unchanged",
        }

    original_count = len(items)
    LOGGER.info("data.dedup: deduplicating %d items on key '%s'", original_count, key_field)

    seen: set = set()
    unique: List[Dict[str, Any]] = []

    for item in items:
        key_value = item.get(key_field)

        # Items without the key field are kept as-is.
        if key_value is None:
            unique.append(item)
            continue

        # Convert unhashable values to their string repr so we can track them.
        try:
            hashable_key = key_value if isinstance(key_value, (str, int, float, bool)) else repr(key_value)
        except Exception:
            hashable_key = id(key_value)

        if hashable_key not in seen:
            seen.add(hashable_key)
            unique.append(item)

    duplicates_removed = original_count - len(unique)
    LOGGER.info(
        "data.dedup: kept %d items, removed %d duplicates",
        len(unique),
        duplicates_removed,
    )
    return {
        "items": unique,
        "count": len(unique),
        "duplicates_removed": duplicates_removed,
    }
