import os
from pathlib import Path

import pytest

from deepagents_okf_backend import OKFBackend

VALID = "---\ntype: Metric\ntitle: X\n---\nbody\n"


@pytest.fixture()
def backend(tmp_path: Path) -> OKFBackend:
    return OKFBackend(tmp_path)


def test_read_non_utf8_returns_error_not_crash(backend: OKFBackend) -> None:
    (backend.root / "bad.bin").write_bytes(b"\xff\xfe\x00\x01")
    res = backend.read("/bad.bin")
    assert res.error is not None
    assert res.file_data is None


def test_read_negative_offset_errors(backend: OKFBackend) -> None:
    backend.write("/m.md", VALID)
    assert backend.read("/m.md", offset=-1).error is not None


def test_write_when_parent_is_a_file_returns_error(backend: OKFBackend) -> None:
    backend.upload_files([("/notes", b"x")])  # /notes is now a regular file
    res = backend.write("/notes/a.md", VALID)  # parent is a file -> NotADirectoryError
    assert res.error is not None  # returned, not raised


def test_edit_does_not_rewrite_frontmatter(tmp_path: Path) -> None:
    be = OKFBackend(tmp_path, validate=False, auto_timestamp=False)
    doc = "---\ntype: Metric\ntags: [a, b]\n---\nhello\n"
    be.write("/d.md", doc)
    assert be.read("/d.md").file_data["content"] == doc  # written verbatim

    be.edit("/d.md", "hello", "world")
    after = be.read("/d.md").file_data["content"]
    assert after == "---\ntype: Metric\ntags: [a, b]\n---\nworld\n"  # frontmatter untouched


def test_edit_making_doc_invalid_has_distinct_error(backend: OKFBackend) -> None:
    backend.write("/m.md", VALID)
    res = backend.edit("/m.md", "type: Metric", "category: Metric")
    assert res.error is not None and "invalid OKF" in res.error
    assert res.occurrences is None
    assert "type: Metric" in backend.read("/m.md").file_data["content"]  # disk untouched


def test_dangling_symlink_is_skipped_by_ls(tmp_path: Path) -> None:
    bundle = tmp_path / "b"
    be = OKFBackend(bundle)
    os.symlink(bundle / "missing.txt", bundle / "dangling.txt")  # contained but broken
    res = be.ls("/")
    assert res.error is None  # stat failure on the dangling link must not crash ls
    assert all(e["path"] != "/dangling.txt" for e in (res.entries or []))


def test_grep_glob_filter_is_recursive(backend: OKFBackend) -> None:
    backend.write("/a/b/deep.md", VALID)
    # grep with a name filter must still find matches in nested dirs
    assert backend.grep("body", glob="*.md").matches
