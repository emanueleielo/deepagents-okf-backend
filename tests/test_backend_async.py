from pathlib import Path

import pytest

from deepagents_okf_backend import OKFBackend

DOC = "---\ntype: Metric\ntitle: WAU\n---\n# weekly active users\n"


@pytest.fixture()
def backend(tmp_path: Path) -> OKFBackend:
    return OKFBackend(tmp_path)


async def test_async_write_read(backend: OKFBackend) -> None:
    w = await backend.awrite("/metrics/wau.md", DOC)
    assert w.error is None
    r = await backend.aread("/metrics/wau.md")
    assert "weekly active users" in r.file_data["content"]


async def test_async_ls_glob_grep_edit(backend: OKFBackend) -> None:
    await backend.awrite("/metrics/wau.md", DOC)
    assert (await backend.als("/metrics")).error is None
    assert (await backend.aglob("**/*.md")).matches
    assert (await backend.agrep("weekly")).matches
    e = await backend.aedit("/metrics/wau.md", "weekly", "monthly")
    assert e.occurrences == 1
