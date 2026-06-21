"""OKF-aware filesystem backend for LangChain Deep Agents."""

from __future__ import annotations

from .backend import OKFBackend
from .frontmatter import parse_frontmatter, serialize_frontmatter
from .okf import KNOWN_FIELDS, REQUIRED_FIELDS, validate_metadata
from .query import OKFHit, make_okf_query_tool, query_bundle

__all__ = [
    "OKFBackend",
    "OKFHit",
    "make_okf_query_tool",
    "query_bundle",
    "parse_frontmatter",
    "serialize_frontmatter",
    "validate_metadata",
    "REQUIRED_FIELDS",
    "KNOWN_FIELDS",
]

__version__ = "0.1.1"
