from __future__ import annotations

import pytest

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json


def test_bounded_json_accepts_plain_protocol_data() -> None:
    assert safe_load_bounded_json(b'{"method":"tools/call","params":{"values":[1,true,null]}}') == {
        "method": "tools/call",
        "params": {"values": [1, True, None]},
    }


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ('{"value":1,"value":2}', "duplicate object key"),
        ('{"value":NaN}', "non-finite"),
        ('{"value":Infinity}', "non-finite"),
        ('{"value":', "valid bounded data"),
    ],
)
def test_bounded_json_rejects_ambiguous_or_invalid_values(
    document: str,
    message: str,
) -> None:
    with pytest.raises(BoundedJSONError, match=message):
        safe_load_bounded_json(document)


def test_bounded_json_ignores_brackets_inside_strings_during_depth_preflight() -> None:
    assert safe_load_bounded_json('{"value":"[[[\\"]]]"}', maximum_depth=1) == {"value": '[[["]]]'}


def test_bounded_json_enforces_depth_and_node_limits() -> None:
    with pytest.raises(BoundedJSONError, match="nesting-depth"):
        safe_load_bounded_json('{"value":[[[1]]]}', maximum_depth=2)
    with pytest.raises(BoundedJSONError, match="structural-node"):
        safe_load_bounded_json('{"value":[1,2,3]}', maximum_nodes=3)


def test_bounded_json_normalizes_python_integer_digit_limits() -> None:
    document = '{"value":' + ("9" * 10_000) + "}"
    with pytest.raises(BoundedJSONError, match="valid bounded data"):
        safe_load_bounded_json(document)


def test_bounded_json_rejects_invalid_utf8_and_non_text() -> None:
    with pytest.raises(BoundedJSONError, match="UTF-8"):
        safe_load_bounded_json(b'{"value":"\xff"}')
    with pytest.raises(TypeError, match="text or bytes"):
        safe_load_bounded_json(123)  # type: ignore[arg-type]


def test_bounded_json_enforces_input_bytes_and_unicode() -> None:
    assert safe_load_bounded_json('{"v":"é"}', maximum_bytes=10) == {"v": "é"}
    with pytest.raises(BoundedJSONError, match="input-byte limit"):
        safe_load_bounded_json('{"v":"é"}', maximum_bytes=9)
    with pytest.raises(BoundedJSONError, match="valid Unicode"):
        safe_load_bounded_json('{"v":"\ud800"}')


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
def test_bounded_json_rejects_invalid_limits(keyword: str, value: object) -> None:
    with pytest.raises(ValueError):
        safe_load_bounded_json("{}", **{keyword: value})
