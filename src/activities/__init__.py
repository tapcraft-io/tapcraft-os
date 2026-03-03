"""Temporal activities module — platform built-ins only."""

# Platform: Generic Data Activities
from src.activities.http_parallel import http_parallel
from src.activities.rss_reader import rss_read
from src.activities.xml_parser import parse_xml
from src.activities.dedup import dedup

__all__ = [
    "http_parallel",
    "rss_read",
    "parse_xml",
    "dedup",
]
