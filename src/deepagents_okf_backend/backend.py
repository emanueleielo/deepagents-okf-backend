"""OKF-aware filesystem backend for LangChain Deep Agents.

``OKFBackend`` implements deepagents' ``BackendProtocol`` over an Open Knowledge
Format (OKF) bundle: a directory of markdown files with YAML frontmatter. Reads and
searches work like a normal virtual filesystem; writes to ``.md`` documents are
validated as OKF and (optionally) auto-stamped with a ``timestamp``.

Every method returns a structured result with an ``error`` field and never raises —
this is the ``BackendProtocol`` contract. All disk IO is therefore guarded, and every
path (including entries discovered by ``ls``/``glob``/``grep``) is confined to the
bundle root, so a symlink inside the bundle cannot leak files from outside it.

OKF spec: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from deepagents.backends.protocol import (
    BackendProtocol,
    EditResult,
    FileData,
    FileDownloadResponse,
    FileInfo,
    FileUploadResponse,
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


def _iso(ts: float) -> str:
    """Format a POSIX timestamp as a second-precision UTC ISO-8601 string."""
    return datetime.fromtimestamp(ts, timezone.utc).replace(microsecond=0).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class OKFBackend(BackendProtocol):
    """A deepagents backend backed by a local OKF bundle directory.

    Args:
        root: Directory holding the OKF bundle. Created if it does not exist.
        validate: When True, writes/edits to ``.md`` docs must be valid OKF
            (``type`` field required) or the operation fails without touching disk.
        auto_timestamp: When True, ``write`` sets/refreshes the ``timestamp``
            frontmatter field on ``.md`` docs that carry frontmatter. ``edit`` never
            rewrites the frontmatter block, so a body-only edit is byte-preserving.
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
        raw = str(path)
        if "\x00" in raw:
            raise _PathEscapeError(path)
        try:
            candidate = (self.root / raw.lstrip("/")).resolve()
        except (OSError, ValueError) as exc:  # malformed path, drive on Windows, etc.
            raise _PathEscapeError(path) from exc
        if not self._is_contained(candidate):
            raise _PathEscapeError(path)
        return candidate

    def _is_contained(self, p: Path) -> bool:
        """Whether ``p`` (after symlink resolution) stays within the bundle root."""
        try:
            resolved = p.resolve()
        except OSError:
            return False
        return resolved == self.root or self.root in resolved.parents

    def _rel(self, p: Path) -> str:
        if p == self.root:
            return "/"
        return "/" + p.relative_to(self.root).as_posix()

    def _safe_file_info(self, p: Path) -> FileInfo | None:
        """Build a FileInfo, or None if the entry vanished / cannot be stat'd."""
        try:
            stat = p.stat()
        except OSError:
            return None
        return FileInfo(
            path=self._rel(p),
            is_dir=p.is_dir(),
            size=stat.st_size,
            modified_at=_iso(stat.st_mtime),
        )

    def _contained_files(self, candidates: Iterable[Path]) -> list[Path]:
        """Filter an iterable of paths to regular files that stay within root."""
        out: list[Path] = []
        for p in sorted(candidates):
            if not self._is_contained(p):
                continue
            try:
                if p.is_file():
                    out.append(p)
            except OSError:
                continue
        return out

    def _stamp_and_validate(self, file_path: str, content: str) -> tuple[str | None, str]:
        """For ``write``: optionally stamp ``timestamp``, then validate OKF.

        Returns ``(error, content)``; ``content`` may be re-serialized to inject the
        timestamp. This is acceptable on a full-content write but never used by ``edit``.
        """
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

    def _validate_only(self, file_path: str, content: str) -> str | None:
        """For ``edit``: validate without mutating ``content``. Returns an error or None."""
        if not is_okf_document(file_path) or not self.validate:
            return None
        metadata, _ = parse_frontmatter(content)
        errors = validate_metadata(metadata)
        if errors:
            return f"edit would make {file_path} invalid OKF: {'; '.join(errors)}"
        return None

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
        try:
            children = sorted(target.iterdir())
        except OSError as exc:
            return LsResult(error=f"cannot list {path}: {exc}")
        entries: list[FileInfo] = []
        for child in children:
            if not self._is_contained(child):
                continue
            info = self._safe_file_info(child)
            if info is not None:
                entries.append(info)
        return LsResult(entries=entries)

    def read(self, file_path: str, offset: int = 0, limit: int = DEFAULT_READ_LIMIT) -> ReadResult:
        try:
            target = self._resolve(file_path)
        except _PathEscapeError:
            return ReadResult(error=f"path escapes bundle root: {file_path}")
        if not target.is_file():
            return ReadResult(error=f"no such file: {file_path}")
        if offset < 0 or limit < 0:
            return ReadResult(error="offset and limit must be non-negative")
        try:
            stat = target.stat()
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return ReadResult(error=f"cannot read {file_path}: {exc}")
        lines = text.splitlines(keepends=True)
        content = "".join(lines[offset : offset + limit])
        file_data = FileData(
            content=content,
            encoding="utf-8",
            created_at=_iso(stat.st_ctime),
            modified_at=_iso(stat.st_mtime),
        )
        return ReadResult(file_data=file_data)

    def write(self, file_path: str, content: str) -> WriteResult:
        try:
            target = self._resolve(file_path)
        except _PathEscapeError:
            return WriteResult(error=f"path escapes bundle root: {file_path}", path=None)
        error, content = self._stamp_and_validate(file_path, content)
        if error:
            return WriteResult(error=error, path=None)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return WriteResult(error=f"cannot write {file_path}: {exc}", path=None)
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
            return EditResult(
                error=f"path escapes bundle root: {file_path}", path=None, occurrences=None
            )
        if not target.is_file():
            return EditResult(error=f"no such file: {file_path}", path=None, occurrences=None)
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return EditResult(error=f"cannot read {file_path}: {exc}", path=None, occurrences=None)
        count = text.count(old_string)
        if count == 0:
            return EditResult(
                error=f"old_string not found in {file_path}", path=None, occurrences=0
            )
        if replace_all:
            new_text, occurrences = text.replace(old_string, new_string), count
        else:
            new_text, occurrences = text.replace(old_string, new_string, 1), 1
        # Validate the result without rewriting the frontmatter block: a body-only
        # edit stays byte-for-byte what the agent asked for.
        error = self._validate_only(file_path, new_text)
        if error:
            return EditResult(error=error, path=None, occurrences=None)
        try:
            target.write_text(new_text, encoding="utf-8")
        except OSError as exc:
            return EditResult(error=f"cannot write {file_path}: {exc}", path=None, occurrences=None)
        return EditResult(error=None, path=self._rel(target), occurrences=occurrences)

    def glob(self, pattern: str, path: str | None = None) -> GlobResult:
        try:
            base = self._resolve(path) if path else self.root
        except _PathEscapeError:
            return GlobResult(error=f"path escapes bundle root: {path}")
        matches: list[FileInfo] = []
        for p in self._contained_files(base.glob(pattern)):
            info = self._safe_file_info(p)
            if info is not None:
                matches.append(info)
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
        # grep is always recursive; the optional `glob` only filters file names.
        candidates = base.rglob(glob) if glob else base.rglob("*")
        matches: list[GrepMatch] = []
        for p in self._contained_files(candidates):
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    matches.append(GrepMatch(path=self._rel(p), line=lineno, text=line))
        return GrepResult(matches=matches)

    # ----------------------------------------------------------------- binary IO
    # Raw byte transfer for non-markdown artifacts (images, exports, attachments).
    # OKF validation is intentionally skipped here — these are opaque blobs.
    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        responses: list[FileUploadResponse] = []
        for file_path, data in files:
            try:
                target = self._resolve(file_path)
            except _PathEscapeError:
                responses.append(FileUploadResponse(path=file_path, error="permission_denied"))
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            except OSError as exc:
                responses.append(FileUploadResponse(path=file_path, error=str(exc)))
                continue
            responses.append(FileUploadResponse(path=self._rel(target), error=None))
        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        responses: list[FileDownloadResponse] = []
        for file_path in paths:
            try:
                target = self._resolve(file_path)
            except _PathEscapeError:
                responses.append(
                    FileDownloadResponse(path=file_path, content=None, error="permission_denied")
                )
                continue
            if not target.is_file():
                responses.append(
                    FileDownloadResponse(path=file_path, content=None, error="file_not_found")
                )
                continue
            try:
                data = target.read_bytes()
            except OSError as exc:
                responses.append(FileDownloadResponse(path=file_path, content=None, error=str(exc)))
                continue
            responses.append(FileDownloadResponse(path=self._rel(target), content=data, error=None))
        return responses

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

    async def aupload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return await asyncio.to_thread(self.upload_files, files)

    async def adownload_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        return await asyncio.to_thread(self.download_files, paths)
