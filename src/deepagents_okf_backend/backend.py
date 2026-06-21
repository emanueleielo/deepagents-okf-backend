"""OKF-aware filesystem backend for LangChain Deep Agents.

``OKFBackend`` implements deepagents' ``BackendProtocol`` over an Open Knowledge
Format (OKF) bundle: a directory of markdown files with YAML frontmatter. Reads and
searches work like a normal virtual filesystem; writes to ``.md`` documents are
validated as OKF and (optionally) auto-stamped with a ``timestamp``.

Every method returns a structured result with an ``error`` field and never raises —
this is the ``BackendProtocol`` contract.

OKF spec: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from deepagents.backends.protocol import (
    BackendProtocol,
    EditResult,
    FileData,
    FileInfo,
    GlobResult,
    GrepMatch,
    GrepResult,
    LsResult,
    ReadResult,
    WriteResult,
)

from .frontmatter import parse_frontmatter, serialize_frontmatter
from .okf import is_okf_document, validate_metadata

DEFAULT_READ_LIMIT = 2000


class _PathEscapeError(Exception):
    """Internal: agent attempted to access a path outside the bundle root."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class OKFBackend(BackendProtocol):
    """A deepagents backend backed by a local OKF bundle directory.

    Args:
        root: Directory holding the OKF bundle. Created if it does not exist.
        validate: When True, writes/edits to ``.md`` docs must be valid OKF
            (``type`` field required) or the operation fails without touching disk.
        auto_timestamp: When True, set/refresh the ``timestamp`` frontmatter field
            on every ``.md`` write that carries frontmatter.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        validate: bool = True,
        auto_timestamp: bool = True,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.validate = validate
        self.auto_timestamp = auto_timestamp
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ helpers
    def _resolve(self, path: str) -> Path:
        """Resolve an agent-supplied path inside the bundle root (no escaping)."""
        candidate = (self.root / str(path).lstrip("/")).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise _PathEscapeError(path)
        return candidate

    def _rel(self, p: Path) -> str:
        if p == self.root:
            return "/"
        return "/" + p.relative_to(self.root).as_posix()

    def _file_info(self, p: Path) -> FileInfo:
        stat = p.stat()
        return FileInfo(
            path=self._rel(p),
            is_dir=p.is_dir(),
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        )

    def _prepare_write(self, file_path: str, content: str) -> tuple[str | None, str]:
        """Apply OKF auto-timestamp + validation. Returns ``(error, content)``."""
        if not is_okf_document(file_path):
            return None, content
        metadata, body = parse_frontmatter(content)
        if self.auto_timestamp and metadata:
            metadata["timestamp"] = _now_iso()
            content = serialize_frontmatter(metadata, body)
        if self.validate:
            errors = validate_metadata(metadata)
            if errors:
                return f"OKF validation failed for {file_path}: {'; '.join(errors)}", content
        return None, content

    # ------------------------------------------------------------------- sync API
    def ls(self, path: str) -> LsResult:
        try:
            target = self._resolve(path)
        except _PathEscapeError:
            return LsResult(error=f"path escapes bundle root: {path}")
        if not target.exists():
            return LsResult(error=f"no such path: {path}")
        if not target.is_dir():
            return LsResult(error=f"not a directory: {path}")
        entries = [self._file_info(child) for child in sorted(target.iterdir())]
        return LsResult(entries=entries)

    def read(self, file_path: str, offset: int = 0, limit: int = DEFAULT_READ_LIMIT) -> ReadResult:
        try:
            target = self._resolve(file_path)
        except _PathEscapeError:
            return ReadResult(error=f"path escapes bundle root: {file_path}")
        if not target.is_file():
            return ReadResult(error=f"no such file: {file_path}")
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        content = "".join(lines[offset : offset + limit])
        stat = target.stat()
        file_data = FileData(
            content=content,
            encoding="utf-8",
            modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        )
        return ReadResult(file_data=file_data)

    def write(self, file_path: str, content: str) -> WriteResult:
        try:
            target = self._resolve(file_path)
        except _PathEscapeError:
            return WriteResult(error=f"path escapes bundle root: {file_path}", path=None)
        error, content = self._prepare_write(file_path, content)
        if error:
            return WriteResult(error=error, path=None)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return WriteResult(error=None, path=self._rel(target))

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        try:
            target = self._resolve(file_path)
        except _PathEscapeError:
            return EditResult(error=f"path escapes bundle root: {file_path}", path=None, occurrences=None)
        if not target.is_file():
            return EditResult(error=f"no such file: {file_path}", path=None, occurrences=None)
        text = target.read_text(encoding="utf-8")
        count = text.count(old_string)
        if count == 0:
            return EditResult(error=f"old_string not found in {file_path}", path=None, occurrences=0)
        if replace_all:
            new_text, occurrences = text.replace(old_string, new_string), count
        else:
            new_text, occurrences = text.replace(old_string, new_string, 1), 1
        error, new_text = self._prepare_write(file_path, new_text)
        if error:
            return EditResult(error=error, path=None, occurrences=None)
        target.write_text(new_text, encoding="utf-8")
        return EditResult(error=None, path=self._rel(target), occurrences=occurrences)

    def glob(self, pattern: str, path: str | None = None) -> GlobResult:
        try:
            base = self._resolve(path) if path else self.root
        except _PathEscapeError:
            return GlobResult(error=f"path escapes bundle root: {path}")
        matches = [self._file_info(p) for p in sorted(base.glob(pattern)) if p.is_file()]
        return GlobResult(matches=matches)

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult:
        try:
            base = self._resolve(path) if path else self.root
        except _PathEscapeError:
            return GrepResult(error=f"path escapes bundle root: {path}")
        candidates = base.glob(glob) if glob else base.rglob("*")
        matches: list[GrepMatch] = []
        for p in sorted(candidates):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    matches.append(GrepMatch(path=self._rel(p), line=lineno, text=line))
        return GrepResult(matches=matches)

    # ------------------------------------------------------------------ async API
    # Local filesystem IO is blocking; offload to a worker thread so async agents
    # never block the event loop.
    async def als(self, path: str) -> LsResult:
        return await asyncio.to_thread(self.ls, path)

    async def aread(
        self, file_path: str, offset: int = 0, limit: int = DEFAULT_READ_LIMIT
    ) -> ReadResult:
        return await asyncio.to_thread(self.read, file_path, offset, limit)

    async def awrite(self, file_path: str, content: str) -> WriteResult:
        return await asyncio.to_thread(self.write, file_path, content)

    async def aedit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        return await asyncio.to_thread(self.edit, file_path, old_string, new_string, replace_all)

    async def aglob(self, pattern: str, path: str | None = None) -> GlobResult:
        return await asyncio.to_thread(self.glob, pattern, path)

    async def agrep(
        self, pattern: str, path: str | None = None, glob: str | None = None
    ) -> GrepResult:
        return await asyncio.to_thread(self.grep, pattern, path, glob)
