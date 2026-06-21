"""YAML frontmatter parsing/serialization for OKF markdown documents.

Pure helper module — intentionally free of any ``deepagents`` import.
"""

from __future__ import annotations

from typing import Any

import yaml

_DELIMITER = "---"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split an OKF markdown document into ``(metadata, body)``.

    A document has frontmatter when it starts with a ``---`` line, followed by a
    YAML block, terminated by another ``---`` line. If there is no frontmatter,
    ``metadata`` is an empty dict and ``body`` is the original text.
    """
    if not text.startswith(_DELIMITER):
        return {}, text

    lines = text.splitlines(keepends=True)
    # lines[0] is the opening delimiter; find the closing one.
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _DELIMITER:
            closing = i
            break
    if closing is None:
        # Unterminated frontmatter block — treat the whole thing as body.
        return {}, text

    raw_yaml = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    loaded = yaml.safe_load(raw_yaml) if raw_yaml.strip() else {}
    metadata = loaded if isinstance(loaded, dict) else {}
    return metadata, body


def serialize_frontmatter(metadata: dict[str, Any], body: str) -> str:
    """Render ``(metadata, body)`` back into an OKF markdown document.

    When ``metadata`` is empty the body is returned unchanged (no frontmatter block).
    """
    if not metadata:
        return body
    dumped = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"{_DELIMITER}\n{dumped}\n{_DELIMITER}\n{body}"


def has_frontmatter(text: str) -> bool:
    """Return whether ``text`` begins with a terminated frontmatter block."""
    metadata, _ = parse_frontmatter(text)
    return bool(metadata)
