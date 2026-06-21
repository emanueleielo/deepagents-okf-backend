"""Semantic query over an OKF bundle, plus a LangChain tool factory.

The six standard filesystem tools only let an agent ``grep`` raw text. OKF frontmatter
(``type``, ``tags``, ``title``) is *structured*, so this module adds a typed query on top
and exposes it as an optional LangChain tool the agent can call directly — kept separate so
``OKFBackend`` itself stays a pure ``BackendProtocol`` implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.tools import BaseTool, tool

from .backend import OKFBackend
from .frontmatter import parse_frontmatter


@dataclass
class OKFHit:
    """A single OKF document matched by :func:`query_bundle`."""

    path: str
    type: str | None = None
    title: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)


def query_bundle(
    backend: OKFBackend,
    *,
    type: str | None = None,
    tags: list[str] | None = None,
    title_contains: str | None = None,
) -> list[OKFHit]:
    """Return OKF documents whose frontmatter matches every supplied filter.

    Filters are ANDed. ``tags`` matches when the document carries *all* given tags.
    ``type`` matches case-insensitively; ``title_contains`` is a case-insensitive substring.
    """
    glob_result = backend.glob("**/*.md")
    if glob_result.error or not glob_result.matches:
        return []

    wanted_tags = {t.lower() for t in (tags or [])}
    hits: list[OKFHit] = []
    for entry in glob_result.matches:
        read_result = backend.read(entry["path"])
        if read_result.error or read_result.file_data is None:
            continue
        metadata, _ = parse_frontmatter(read_result.file_data["content"])
        if not metadata:
            continue

        doc_type = metadata.get("type")
        if type is not None and (doc_type or "").lower() != type.lower():
            continue

        raw_tags = metadata.get("tags") or []
        # A malformed bundle may store `tags` as a bare string; normalize to a list
        # so we never iterate it character-by-character.
        doc_tags = raw_tags if isinstance(raw_tags, list) else [raw_tags]
        if wanted_tags and not wanted_tags.issubset({str(t).lower() for t in doc_tags}):
            continue

        doc_title = metadata.get("title")
        if title_contains is not None and title_contains.lower() not in (doc_title or "").lower():
            continue

        hits.append(
            OKFHit(
                path=entry["path"],
                type=doc_type,
                title=doc_title,
                description=metadata.get("description"),
                tags=[str(t) for t in doc_tags],
            )
        )
    return hits


def _format_hits(hits: list[OKFHit]) -> str:
    if not hits:
        return "No matching OKF documents found."
    lines = [f"Found {len(hits)} document(s):"]
    for h in hits:
        parts = [f"- {h.path}"]
        if h.type:
            parts.append(f"[{h.type}]")
        if h.title:
            parts.append(h.title)
        line = " ".join(parts)
        if h.description:
            line += f" — {h.description}"
        if h.tags:
            line += f" (tags: {', '.join(h.tags)})"
        lines.append(line)
    return "\n".join(lines)


def make_okf_query_tool(backend: OKFBackend) -> BaseTool:
    """Build a LangChain tool that lets an agent query the OKF bundle by frontmatter.

    Add the returned tool to ``create_deep_agent(tools=[...])`` so the agent can do
    structured lookups (by ``type``/``tags``/``title``) instead of blind ``grep``.
    """

    @tool
    def okf_query(
        type: str | None = None,
        tags: list[str] | None = None,
        title_contains: str | None = None,
    ) -> str:
        """Search the OKF knowledge bundle by frontmatter fields.

        Args:
            type: Match documents whose ``type`` equals this (case-insensitive),
                e.g. "BigQuery Table" or "Metric".
            tags: Match documents carrying all of these tags.
            title_contains: Match documents whose title contains this substring.
        """
        return _format_hits(
            query_bundle(backend, type=type, tags=tags, title_contains=title_contains)
        )

    return okf_query
