from deepagents_okf_backend.frontmatter import (
    has_frontmatter,
    parse_frontmatter,
    serialize_frontmatter,
)

DOC = """---
type: BigQuery Table
title: Orders
tags: [sales, revenue]
---
# Schema
body line
"""


def test_parse_extracts_metadata_and_body() -> None:
    metadata, body = parse_frontmatter(DOC)
    assert metadata["type"] == "BigQuery Table"
    assert metadata["tags"] == ["sales", "revenue"]
    assert body.startswith("# Schema")


def test_no_frontmatter_returns_empty_metadata() -> None:
    metadata, body = parse_frontmatter("# just markdown")
    assert metadata == {}
    assert body == "# just markdown"


def test_unterminated_frontmatter_is_treated_as_body() -> None:
    text = "---\ntype: X\nno closing delimiter"
    metadata, body = parse_frontmatter(text)
    assert metadata == {}
    assert body == text


def test_round_trip_preserves_fields_and_body() -> None:
    metadata, body = parse_frontmatter(DOC)
    rebuilt = serialize_frontmatter(metadata, body)
    again_meta, again_body = parse_frontmatter(rebuilt)
    assert again_meta == metadata
    assert again_body == body


def test_serialize_without_metadata_returns_body() -> None:
    assert serialize_frontmatter({}, "# body") == "# body"


def test_has_frontmatter() -> None:
    assert has_frontmatter(DOC)
    assert not has_frontmatter("# nope")
