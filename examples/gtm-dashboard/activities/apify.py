"""Apify activities - run actors and retrieve results."""

from __future__ import annotations

import logging
from typing import Any, Dict

import httpx
from temporalio import activity

from src.services.secrets import get_secret

LOGGER = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"


@activity.defn(name="apify.run_actor")
async def run_actor(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start an Apify actor run.

    Args:
        config: Dict containing:
            - actor_id: The Apify actor ID (e.g. "apify/web-scraper")
            - input_data: Dict of input parameters for the actor

    Returns:
        Dict with run_id and status of the started run.
    """
    actor_id = config.get("actor_id", "")
    input_data = config.get("input_data", {})

    if not actor_id:
        return {"run_id": None, "status": "FAILED", "error": "No actor_id specified"}

    try:
        token = await get_secret("apify_api_key")
    except KeyError:
        return {
            "run_id": None,
            "status": "FAILED",
            "error": "Secret 'apify_api_key' not configured. "
                     "Add it via Settings > Secrets.",
        }

    url = f"{APIFY_BASE}/acts/{actor_id}/runs"

    LOGGER.info(f"Starting Apify actor '{actor_id}'")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"token": token},
                json=input_data,
                timeout=60.0,
            )
            response.raise_for_status()

        result = response.json()
        run_data = result.get("data", {})
        run_id = run_data.get("id", "")
        status = run_data.get("status", "UNKNOWN")

        LOGGER.info(f"Apify actor '{actor_id}' started: run_id={run_id}, status={status}")
        return {"run_id": run_id, "status": status}

    except httpx.HTTPStatusError as e:
        LOGGER.error(f"HTTP error starting Apify actor '{actor_id}': {e.response.status_code}")
        return {
            "run_id": None,
            "status": "FAILED",
            "error": f"HTTP {e.response.status_code}: {str(e)}",
        }
    except Exception as e:
        LOGGER.error(f"Error starting Apify actor '{actor_id}': {e}")
        return {"run_id": None, "status": "FAILED", "error": str(e)}


@activity.defn(name="apify.get_results")
async def get_results(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get results from a completed Apify actor run.

    First fetches the run details to get the default dataset ID,
    then fetches items from that dataset.

    Args:
        config: Dict containing:
            - run_id: The Apify run ID returned by run_actor

    Returns:
        Dict with items list and count.
    """
    run_id = config.get("run_id", "")

    if not run_id:
        return {"items": [], "count": 0, "error": "No run_id specified"}

    try:
        token = await get_secret("apify_api_key")
    except KeyError:
        return {
            "items": [],
            "count": 0,
            "error": "Secret 'apify_api_key' not configured. "
                     "Add it via Settings > Secrets.",
        }

    LOGGER.info(f"Fetching results for Apify run '{run_id}'")

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Get the run details to find the default dataset ID
            run_url = f"{APIFY_BASE}/actor-runs/{run_id}"
            run_response = await client.get(
                run_url,
                params={"token": token},
                timeout=30.0,
            )
            run_response.raise_for_status()

            run_data = run_response.json().get("data", {})
            run_status = run_data.get("status", "UNKNOWN")
            dataset_id = run_data.get("defaultDatasetId", "")

            if not dataset_id:
                return {
                    "items": [],
                    "count": 0,
                    "status": run_status,
                    "error": "No default dataset found for this run",
                }

            if run_status not in ("SUCCEEDED", "RUNNING"):
                return {
                    "items": [],
                    "count": 0,
                    "status": run_status,
                    "error": f"Run is in status '{run_status}', results may not be available",
                }

            # Step 2: Fetch items from the dataset
            dataset_url = f"{APIFY_BASE}/datasets/{dataset_id}/items"
            dataset_response = await client.get(
                dataset_url,
                params={"token": token},
                timeout=60.0,
            )
            dataset_response.raise_for_status()

            items = dataset_response.json()
            # The dataset items endpoint returns a list directly
            if not isinstance(items, list):
                items = []

        LOGGER.info(
            f"Fetched {len(items)} items from Apify run '{run_id}' "
            f"(dataset: {dataset_id})"
        )
        return {"items": items, "count": len(items), "status": run_status}

    except httpx.HTTPStatusError as e:
        LOGGER.error(
            f"HTTP error fetching Apify results for run '{run_id}': "
            f"{e.response.status_code}"
        )
        return {
            "items": [],
            "count": 0,
            "error": f"HTTP {e.response.status_code}: {str(e)}",
        }
    except Exception as e:
        LOGGER.error(f"Error fetching Apify results for run '{run_id}': {e}")
        return {"items": [], "count": 0, "error": str(e)}
