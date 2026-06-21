from pathlib import Path

import pytest

from deepagents_okf_backend import OKFBackend, make_okf_query_tool, query_bundle

TABLE = "---\ntype: BigQuery Table\ntitle: Orders\ntags: [sales, revenue]\n---\n# Orders\n"
METRIC = "---\ntype: Metric\ntitle: Weekly Active Users\ntags: [growth]\n---\n# WAU\n"


@pytest.fixture()
def backend(tmp_path: Path) -> OKFBackend:
    be = OKFBackend(tmp_path)
    be.write("/tables/orders.md", TABLE)
    be.write("/metrics/wau.md", METRIC)
    return be


def test_query_by_type_is_case_insensitive(backend: OKFBackend) -> None:
    hits = query_bundle(backend, type="bigquery table")
    assert [h.path for h in hits] == ["/tables/orders.md"]
    assert hits[0].title == "Orders"


def test_query_by_tags_requires_all(backend: OKFBackend) -> None:
    assert len(query_bundle(backend, tags=["sales"])) == 1
    assert query_bundle(backend, tags=["sales", "growth"]) == []


def test_query_by_title_substring(backend: OKFBackend) -> None:
    hits = query_bundle(backend, title_contains="active")
    assert [h.path for h in hits] == ["/metrics/wau.md"]


def test_query_no_filters_returns_all(backend: OKFBackend) -> None:
    assert len(query_bundle(backend)) == 2


def test_query_string_tags_do_not_match_per_character(tmp_path: Path) -> None:
    be = OKFBackend(tmp_path, validate=False, auto_timestamp=False)
    be.write("/d.md", "---\ntype: X\ntags: prod\n---\nbody\n")  # tags is a bare string
    assert [h.path for h in query_bundle(be, tags=["prod"])] == ["/d.md"]
    assert query_bundle(be, tags=["p"]) == []  # must NOT match a single character


def test_query_tool_returns_readable_text(backend: OKFBackend) -> None:
    okf_query = make_okf_query_tool(backend)
    out = okf_query.invoke({"type": "Metric"})
    assert "Weekly Active Users" in out
    assert "/metrics/wau.md" in out

    empty = okf_query.invoke({"type": "Nonexistent"})
    assert "No matching" in empty
