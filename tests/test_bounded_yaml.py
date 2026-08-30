from __future__ import annotations

import pytest

from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded


def test_bounded_yaml_accepts_plain_configuration_data() -> None:
    assert safe_load_bounded("profile: standard\nvalues: [one, 2, true, null]\n") == {
        "profile": "standard",
        "values": ["one", 2, True, None],
    }


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("value: 1\nvalue: 2\n", "duplicate mapping key"),
        ("base: &base [one]\ncopy: *base\n", "aliases"),
        ("value: {<<: {nested: true}}\n", "merge keys"),
        ("value: .nan\n", "non-finite"),
        ("1: value\n", "keys must be text"),
    ],
)
def test_bounded_yaml_rejects_ambiguous_or_nonportable_values(
    document: str,
    message: str,
) -> None:
    with pytest.raises(BoundedYAMLError, match=message):
        safe_load_bounded(document)


def test_bounded_yaml_enforces_depth_and_node_limits() -> None:
    with pytest.raises(BoundedYAMLError, match="nesting-depth"):
        safe_load_bounded("value: [[[one]]]", maximum_depth=2)
    with pytest.raises(BoundedYAMLError, match="structural-node"):
        safe_load_bounded("value: [one, two, three]", maximum_nodes=3)


def test_bounded_yaml_rejects_invalid_utf8_and_malformed_yaml() -> None:
    with pytest.raises(BoundedYAMLError, match="UTF-8"):
        safe_load_bounded(b"value: \xff")
    with pytest.raises(BoundedYAMLError, match="valid bounded data"):
        safe_load_bounded("value: [unterminated")


def test_bounded_yaml_enforces_input_bytes_and_unicode() -> None:
    assert safe_load_bounded("v: é\n", maximum_bytes=6) == {"v": "é"}
    with pytest.raises(BoundedYAMLError, match="input-byte limit"):
        safe_load_bounded("v: é\n", maximum_bytes=5)
    with pytest.raises(BoundedYAMLError, match="valid Unicode"):
        safe_load_bounded("v: \ud800\n")


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("maximum_bytes", 0),
        ("maximum_bytes", True),
        ("maximum_bytes", 1.5),
        ("maximum_depth", 0),
        ("maximum_depth", True),
        ("maximum_depth", 1.5),
        ("maximum_nodes", 0),
        ("maximum_nodes", True),
        ("maximum_nodes", 1.5),
    ],
)
def test_bounded_yaml_rejects_invalid_limits(keyword: str, value: object) -> None:
    with pytest.raises(ValueError):
        safe_load_bounded("{}", **{keyword: value})


def test_bounded_yaml_requires_text_or_bytes() -> None:
    with pytest.raises(TypeError, match="text or bytes"):
        safe_load_bounded(123)  # type: ignore[arg-type]
