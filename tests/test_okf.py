from deepagents_okf_backend.okf import is_okf_document, validate_metadata


def test_valid_minimal_document() -> None:
    assert validate_metadata({"type": "Metric"}) == []


def test_missing_type_is_an_error() -> None:
    errors = validate_metadata({"title": "Orders"})
    assert any("type" in e for e in errors)


def test_empty_type_is_an_error() -> None:
    assert validate_metadata({"type": ""}) != []


def test_tags_must_be_list_of_strings() -> None:
    assert validate_metadata({"type": "X", "tags": "sales"}) != []
    assert validate_metadata({"type": "X", "tags": [1, 2]}) != []
    assert validate_metadata({"type": "X", "tags": ["sales"]}) == []


def test_string_fields_reject_non_strings() -> None:
    assert validate_metadata({"type": "X", "title": 123}) != []


def test_is_okf_document() -> None:
    assert is_okf_document("/tables/orders.md")
    assert not is_okf_document("/data/orders.csv")
