from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import agency_runtime.core.bounded_json as bounded_json_module
from agency_runtime.adapters.openclaw.node_bridge import _outbound_binding_matches_policy_text
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.store.child_routing import _decode_cache_decision
from agency_runtime.core.store.projections import (
    RUN_METADATA_LIMIT,
    RUN_METADATA_MAX_NODES,
    decode_run_metadata,
    project_run_metadata,
)
from agency_runtime.core.store.workforce import _decoded as decode_workforce_evidence


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


def test_node_limit_rejects_before_json_materialization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bounded_json_module.json,
        "loads",
        lambda *_args, **_kwargs: pytest.fail("over-wide JSON reached json.loads"),
    )

    with pytest.raises(BoundedJSONError, match="structural-node"):
        safe_load_bounded_json("[" + ",".join("0" for _ in range(100)) + "]", maximum_nodes=10)


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


def test_persisted_run_metadata_fails_closed_at_every_json_limit() -> None:
    excessive_nodes = json.dumps(
        {f"field_{index}": index for index in range(RUN_METADATA_MAX_NODES)}
    )
    excessive_bytes = json.dumps({"source": "x" * RUN_METADATA_LIMIT})
    for document in (
        '{"source":"first","source":"second"}',
        '{"state_revision":NaN}',
        '{"source":{"nested":{"too_deep":true}}}',
        excessive_nodes,
        excessive_bytes,
    ):
        assert decode_run_metadata(document) == {}

    assert decode_run_metadata(b'{"source":"hook","state_revision":7}') == {
        "source": "hook",
        "state_revision": 7,
    }
    assert project_run_metadata({"state_revision": float("nan")}) is None


def test_persisted_and_outbound_decoders_reject_duplicate_key_ambiguity() -> None:
    assert _decode_cache_decision('{"selected":"first","selected":"second"}') is None
    with pytest.raises(RuntimeError, match="stored workforce evidence is invalid"):
        decode_workforce_evidence('{"approved":false,"approved":true}')
    assert not _outbound_binding_matches_policy_text(
        '{"text":"draft","text":"final"}',
        "final",
    )


def test_direct_json_loads_are_limited_to_documented_owned_generators() -> None:
    package_root = Path(__file__).resolve().parents[1] / "agency_runtime"
    occurrences: dict[str, int] = {}
    for source_path in package_root.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        relative = source_path.relative_to(package_root).as_posix()
        occurrences[relative] = source.count("json.loads(")

        tree = ast.parse(source, filename=str(source_path))
        module_aliases = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
            if alias.name == "json"
        }
        load_aliases = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "json"
            for alias in node.names
            if alias.name == "loads"
        }
        direct_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "loads"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in module_aliases
                )
                or (isinstance(node.func, ast.Name) and node.func.id in load_aliases)
            )
        ]
        if relative in {"core/bounded_json.py", "core/selector/judge_protocol.py"}:
            assert len(direct_calls) == 1
        else:
            assert direct_calls == []

    assert {path: count for path, count in occurrences.items() if count} == {
        "core/bounded_json.py": 1,
        "core/evals/product_validators_extended.py": 1,
        "core/installer_payload_hermes.py": 1,
        "core/owned_process_linux.py": 1,
        "core/selector/judge_protocol.py": 1,
    }
