"""Open Knowledge Format (OKF) v0.1 conventions and validation.

Pure helper module — intentionally free of any ``deepagents`` import.

Spec: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
"""

from __future__ import annotations

from typing import Any

#: The only frontmatter field OKF v0.1 makes mandatory.
REQUIRED_FIELDS: tuple[str, ...] = ("type",)

#: Structured fields OKF v0.1 gives meaning to. Everything else is producer-optional.
KNOWN_FIELDS: tuple[str, ...] = (
    "type",
    "title",
    "description",
    "resource",
    "tags",
    "timestamp",
)

#: Conventional per-directory index document.
INDEX_FILENAME = "index.md"

#: Extension of OKF concept documents.
DOC_SUFFIX = ".md"


class OKFValidationError(ValueError):
    """Raised by strict helpers when a document violates OKF v0.1."""


def validate_metadata(metadata: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty list == valid).

    OKF v0.1 only requires ``type``. We additionally sanity-check the shape of a
    couple of well-known fields so the agent cannot write a structurally broken doc.
    """
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in metadata or metadata[field] in (None, ""):
            errors.append(f"missing required OKF field: '{field}'")

    tags = metadata.get("tags")
    if tags is not None and not (
        isinstance(tags, list) and all(isinstance(t, str) for t in tags)
    ):
        errors.append("'tags' must be a list of strings")

    for field in ("type", "title", "description", "resource", "timestamp"):
        value = metadata.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"'{field}' must be a string")

    return errors


def is_okf_document(path: str) -> bool:
    """Whether ``path`` looks like an OKF concept document (a ``.md`` file)."""
    return path.endswith(DOC_SUFFIX)
