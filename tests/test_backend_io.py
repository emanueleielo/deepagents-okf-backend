from pathlib import Path

import pytest

from deepagents_okf_backend import OKFBackend

VALID_DOC = """---
type: BigQuery Table
title: Orders
tags: [sales, revenue]
---
# Schema
order_id STRING
"""


@pytest.fixture()
def backend(tmp_path: Path) -> OKFBackend:
    return OKFBackend(tmp_path)


def test_write_then_read_roundtrip(backend: OKFBackend) -> None:
    w = backend.write("/tables/orders.md", VALID_DOC)
    assert w.error is None
    assert w.path == "/tables/orders.md"

    r = backend.read("/tables/orders.md")
    assert r.error is None
    assert "order_id STRING" in r.file_data["content"]


def test_write_rejects_invalid_okf(backend: OKFBackend) -> None:
    w = backend.write("/tables/broken.md", "# no frontmatter")
    assert w.error is not None
    assert not (backend.root / "tables/broken.md").exists()  # nothing written


def test_validation_can_be_disabled(tmp_path: Path) -> None:
    be = OKFBackend(tmp_path, validate=False)
    assert be.write("/notes.md", "# free form").error is None


def test_auto_timestamp_is_stamped(backend: OKFBackend) -> None:
    backend.write("/m.md", "---\ntype: Metric\n---\nbody\n")
    content = backend.read("/m.md").file_data["content"]
    assert "timestamp:" in content


def test_ls_lists_entries(backend: OKFBackend) -> None:
    backend.write("/tables/orders.md", VALID_DOC)
    result = backend.ls("/tables")
    assert result.error is None
    assert any(e["path"] == "/tables/orders.md" for e in result.entries)


def test_glob_matches(backend: OKFBackend) -> None:
    backend.write("/tables/orders.md", VALID_DOC)
    result = backend.glob("**/*.md")
    assert any(m["path"] == "/tables/orders.md" for m in result.matches)


def test_grep_finds_literal(backend: OKFBackend) -> None:
    backend.write("/tables/orders.md", VALID_DOC)
    result = backend.grep("revenue")
    assert result.error is None
    assert result.matches and result.matches[0]["path"] == "/tables/orders.md"


def test_edit_replaces(backend: OKFBackend) -> None:
    backend.write("/tables/orders.md", VALID_DOC)
    e = backend.edit("/tables/orders.md", "order_id STRING", "order_id INT64")
    assert e.error is None
    assert e.occurrences == 1
    assert "INT64" in backend.read("/tables/orders.md").file_data["content"]


def test_edit_missing_string_errors(backend: OKFBackend) -> None:
    backend.write("/tables/orders.md", VALID_DOC)
    e = backend.edit("/tables/orders.md", "nonexistent", "x")
    assert e.error is not None
    assert e.occurrences == 0


def test_path_escape_is_blocked(backend: OKFBackend) -> None:
    assert backend.read("/../../etc/passwd").error is not None
    assert backend.write("/../escape.md", VALID_DOC).error is not None
