"""XML parsing activity for Temporal workflows."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from temporalio import activity

LOGGER = logging.getLogger(__name__)


def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
    """Recursively convert an ElementTree element to a nested dict.

    Structure:
        {
            "tag": "tagname",
            "attrib": {...},          # only if attributes exist
            "text": "...",            # only if non-empty text
            "children": [...]         # only if child elements exist
        }
    """
    node: Dict[str, Any] = {"tag": element.tag}

    if element.attrib:
        node["attrib"] = dict(element.attrib)

    text = (element.text or "").strip()
    if text:
        node["text"] = text

    children: List[Dict[str, Any]] = []
    for child in element:
        children.append(_element_to_dict(child))
        # Capture any tail text after child elements.
        tail = (child.tail or "").strip()
        if tail:
            children.append({"tag": "__tail__", "text": tail})

    if children:
        node["children"] = children

    return node


@activity.defn(name="data.parse_xml")
async def parse_xml(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse an XML string into a nested dict representation.

    Args:
        config: Dict containing:
            - xml_string: The raw XML content to parse.

    Returns:
        dict with ``result`` (the nested dict) or an error description.
    """
    xml_string = config.get("xml_string", "")

    if not xml_string:
        return {"result": {}, "error": "No xml_string provided"}

    LOGGER.info("data.parse_xml: parsing XML (%d chars)", len(xml_string))

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as exc:
        LOGGER.error("data.parse_xml: parse error: %s", exc)
        return {"result": {}, "error": f"XML parse error: {exc}"}

    result = _element_to_dict(root)
    LOGGER.info("data.parse_xml: completed successfully")
    return {"result": result}
