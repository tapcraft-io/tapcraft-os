"""ArXiv activity - search papers via the ArXiv API."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import httpx
from temporalio import activity

LOGGER = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


@activity.defn(name="arxiv.search")
async def search(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search ArXiv papers by category and/or keywords.

    Args:
        config: Dict containing:
            - categories: List of ArXiv categories (e.g. ["cs.AI", "cs.LG"])
            - keywords: List of keyword strings to search for
            - max_results: Maximum number of results (default 20)

    Returns:
        Dict with papers list, each containing title, url, authors,
        abstract, and published.
    """
    categories: List[str] = config.get("categories", [])
    keywords: List[str] = config.get("keywords", [])
    max_results = config.get("max_results", 20)

    search_query = _build_search_query(categories, keywords)
    if not search_query:
        return {"papers": [], "error": "No categories or keywords specified"}

    LOGGER.info(
        f"Searching ArXiv: query='{search_query}', max_results={max_results}"
    )

    try:
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                ARXIV_API,
                params=params,
                timeout=30.0,
                follow_redirects=True,
            )
            response.raise_for_status()

        papers = _parse_atom_response(response.text)

        LOGGER.info(f"Found {len(papers)} ArXiv papers")
        return {"papers": papers}

    except httpx.HTTPStatusError as e:
        LOGGER.error(f"HTTP error searching ArXiv: {e.response.status_code}")
        return {"papers": [], "error": f"HTTP {e.response.status_code}: {str(e)}"}
    except Exception as e:
        LOGGER.error(f"Error searching ArXiv: {e}")
        return {"papers": [], "error": str(e)}


def _build_search_query(
    categories: List[str], keywords: List[str]
) -> str:
    """Build an ArXiv API search query from categories and keywords.

    Categories are combined with OR, keywords are combined with OR,
    and the two groups are ANDed together (when both are present).
    """
    parts = []

    if categories:
        cat_terms = [f"cat:{cat}" for cat in categories]
        if len(cat_terms) == 1:
            parts.append(cat_terms[0])
        else:
            parts.append("(" + " OR ".join(cat_terms) + ")")

    if keywords:
        kw_terms = [f"all:{kw}" for kw in keywords]
        if len(kw_terms) == 1:
            parts.append(kw_terms[0])
        else:
            parts.append("(" + " OR ".join(kw_terms) + ")")

    return " AND ".join(parts)


def _parse_atom_response(xml_text: str) -> List[Dict[str, Any]]:
    """Parse the Atom XML response from ArXiv into a list of paper dicts."""
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall(f"{ATOM_NS}entry"):
        title_el = entry.find(f"{ATOM_NS}title")
        title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

        # The paper URL is the id element
        id_el = entry.find(f"{ATOM_NS}id")
        url = id_el.text.strip() if id_el is not None and id_el.text else ""

        # Authors
        authors = []
        for author_el in entry.findall(f"{ATOM_NS}author"):
            name_el = author_el.find(f"{ATOM_NS}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        # Abstract (summary)
        summary_el = entry.find(f"{ATOM_NS}summary")
        abstract = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""

        # Published date
        published_el = entry.find(f"{ATOM_NS}published")
        published = published_el.text.strip() if published_el is not None and published_el.text else ""

        papers.append({
            "title": title,
            "url": url,
            "authors": authors,
            "abstract": abstract,
            "published": published,
        })

    return papers
