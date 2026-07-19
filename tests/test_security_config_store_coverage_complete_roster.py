from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import pytest

from agency_runtime.core.roster import ingress, sync


def _agent(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": "candidate-1",
        "slug": "agent-one",
        "name": "Agent One",
        "description": "A useful agent",
        "prompt_body": "Do useful work",
        "content": "Do useful work",
        "version": "1.0.0",
    }
    value.update(overrides)
    return ingress._normalize_agent(value)


def test_roster_text_and_structure_limits_reject_ambiguous_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert ingress._require_bounded_text(None, 10, "value") == ""
    assert ingress._require_bounded_text(3.5, 10, "value") == "3.5"
    with pytest.raises(ingress.RosterSyncError, match="must be text"):
        ingress._require_bounded_text(object(), 10, "value")
    with pytest.raises(ingress.RosterSyncError, match="unsafe control"):
        ingress._require_bounded_text("bad\0value", 20, "value")

    monkeypatch.setattr(ingress, "MAX_DOCUMENT_NODES", 1)
    with pytest.raises(ingress.RosterSyncError, match="structural node"):
        ingress._validate_structure([1], "document")
    monkeypatch.setattr(ingress, "MAX_DOCUMENT_NODES", 100)
    monkeypatch.setattr(ingress, "MAX_DOCUMENT_DEPTH", 0)
    with pytest.raises(ingress.RosterSyncError, match="nesting depth"):
        ingress._validate_structure([1], "document")
    monkeypatch.setattr(ingress, "MAX_DOCUMENT_DEPTH", 64)

    shared: list[str] = []
    for value, message in (
        ({"first": shared, "second": shared}, "cycle or shared"),
        ({1: "value"}, "mapping keys must be text"),
        (float("nan"), "non-finite"),
        (object(), "unsupported value type"),
    ):
        with pytest.raises(ingress.RosterSyncError, match=message):
            ingress._validate_structure(value, "document")
    shared_mapping: dict[str, Any] = {}
    with pytest.raises(ingress.RosterSyncError, match="cycle or shared"):
        ingress._validate_structure({"first": shared_mapping, "second": shared_mapping}, "document")


def test_roster_yaml_and_list_normalization_error_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ingress,
        "safe_load_bounded",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RecursionError()),
    )
    with pytest.raises(ingress.RosterSyncError, match="not valid bounded YAML"):
        ingress._load_yaml("value", "agent YAML")
    monkeypatch.undo()
    assert ingress._load_yaml("value: 1", "agent YAML") == {"value": 1}

    assert ingress._json_list('["a", "b"]') == ["a", "b"]
    assert ingress._json_list(["", "a"]) == ["a"]
    assert ingress._json_list("{}") == ["{}"]
    assert ingress._json_list("a, b") == ["a", "b"]
    assert ingress._json_list({"b", "a"}) == ["a", "b"]
    assert ingress._json_list(7) == ["7"]
    with pytest.raises(ingress.RosterSyncError):
        ingress._json_list("[invalid")


def test_agent_normalization_and_parser_contract_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ingress.RosterSyncError, match="must be a mapping"):
        ingress._normalize_agent([])  # type: ignore[arg-type]
    monkeypatch.setattr(
        ingress.json,
        "dumps",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("not serializable")),
    )
    with pytest.raises(ingress.RosterSyncError, match="not JSON serializable"):
        ingress._normalize_agent(
            {
                "slug": "agent-one",
                "name": "Agent",
                "description": "description",
                "prompt_body": "",
            }
        )
    monkeypatch.undo()

    with pytest.raises(ValueError, match="empty"):
        ingress.parse_agent_file("  ")
    with pytest.raises(ValueError, match="unterminated"):
        ingress.parse_agent_file("---\nslug: agent")
    monkeypatch.setattr(ingress, "_load_json", lambda *_args: [])
    with pytest.raises(ValueError, match="must be an object"):
        ingress.parse_agent_file("{}")
    monkeypatch.setattr(ingress, "_load_yaml", lambda *_args: ["not a mapping"])
    with pytest.raises(ValueError, match="front matter must be a mapping"):
        ingress.parse_agent_file("---\nvalue\n---\nbody")
    with pytest.raises(ValueError, match="YAML agent file must be a mapping"):
        ingress.parse_agent_file("slug: agent")
    monkeypatch.undo()
    assert (
        ingress.parse_agent_file("---\nslug: agent-one\nname: Agent\ndescription: Desc\n---\nBody")[
            "slug"
        ]
        == "agent-one"
    )
    assert (
        ingress.parse_agent_file(
            "slug: agent-two\nname: Agent\ndescription: Desc\nprompt_body: Body"
        )["slug"]
        == "agent-two"
    )


def test_source_decoding_labels_and_specification_guards(tmp_path: Path) -> None:
    with pytest.raises(ingress.RosterSyncError, match="UTF-8"):
        ingress._decode_source(b"\xff", "source")
    assert ingress._source_label("custom:value") == "custom:value"
    assert ingress._source_label("https://[::1]/agents?secret=x") == "https://[::1]/agents"

    for value, message in (
        ("https://example.test/bad path", "whitespace"),
        ("https://example.test/ümlaut", "percent-encode"),
        ("https:///missing", "hostname"),
    ):
        with pytest.raises(ingress.RosterSyncError, match=message):
            ingress._validated_http_source(value, urlsplit(value))
    with pytest.raises(ingress.RosterSyncError, match="query or fragment"):
        ingress._file_source_path(urlsplit("file:///tmp/agent?query=1"))
    with pytest.raises(ingress.RosterSyncError, match="credentials"):
        ingress._file_source_path(urlsplit("file://user:pass@localhost/tmp/agent"))
    with pytest.raises(ingress.RosterSyncError, match="unsupported roster source scheme"):
        ingress._existing_local_source("unknown://missing", "unknown")
    assert ingress._existing_local_source(str(tmp_path), "c")[0] == "path"
    with pytest.raises(ingress.RosterSyncError, match="must be text"):
        ingress._validate_source_spec(1)  # type: ignore[arg-type]
    assert ingress._validate_source_spec(str(tmp_path))[0] == "path"


def test_http_status_and_bounded_response_reader_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert ingress._response_status(SimpleNamespace(getcode=lambda: 204)) == 204
    with pytest.raises(ingress.RosterSyncError, match="valid status"):
        ingress._response_status(SimpleNamespace(status=True))
    ingress._validate_response_headers(SimpleNamespace(headers={}))

    class Response:
        status = 200

        def __init__(self, chunks: list[Any]) -> None:
            self.chunks = iter(chunks)
            self.headers = {"Content-Type": "application/json"}

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def geturl(self) -> str:
            return "https://example.test/agents"

        def read(self, _size: int) -> Any:
            return next(self.chunks)

    monkeypatch.setattr(
        ingress,
        "open_no_redirect",
        lambda *_args, **_kwargs: Response([b""]),
    )
    times = iter((0.0, 1.0, 100.0))
    monkeypatch.setattr(ingress, "monotonic", lambda: next(times))
    with pytest.raises(ingress.RosterSyncError, match="total deadline"):
        ingress._read_http_source("https://example.test/agents")

    monkeypatch.setattr(
        ingress,
        "open_no_redirect",
        lambda *_args, **_kwargs: Response([b""]),
    )
    times = iter((0.0, 100.0))
    monkeypatch.setattr(ingress, "monotonic", lambda: next(times))
    with pytest.raises(ingress.RosterSyncError, match="total deadline"):
        ingress._read_http_source("https://example.test/agents")

    monkeypatch.setattr(
        ingress,
        "open_no_redirect",
        lambda *_args, **_kwargs: Response(["not bytes"]),
    )
    monkeypatch.setattr(ingress, "monotonic", lambda: 0.0)
    with pytest.raises(ingress.RosterSyncError, match="non-byte content"):
        ingress._read_http_source("https://example.test/agents")

    monkeypatch.setattr(
        ingress,
        "open_no_redirect",
        lambda *_args, **_kwargs: Response([b""]),
    )
    monkeypatch.setattr(ingress, "monotonic", lambda: 0.0)
    response = Response([b""])
    response.headers["Content-Length"] = "0"
    monkeypatch.setattr(ingress, "open_no_redirect", lambda *_args, **_kwargs: response)
    assert ingress._read_http_source("https://example.test/agents") == ""


def test_local_file_and_directory_race_errors_close_descriptors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.md"
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda path: path)
    with pytest.raises(ingress.RosterSyncError, match="unavailable"):
        ingress._read_local_file(missing)

    with pytest.raises(ingress.RosterSyncError, match="regular file"):
        ingress._read_local_file(tmp_path)

    file_path = tmp_path / "agent.md"
    file_path.write_text("# Agent", encoding="utf-8")
    closed: list[int] = []
    monkeypatch.setattr(ingress.os, "O_NOFOLLOW", 0x4000, raising=False)
    monkeypatch.setattr(ingress.os, "open", lambda *_args: 91)
    monkeypatch.setattr(
        ingress.os,
        "fstat",
        lambda _descriptor: (_ for _ in ()).throw(OSError("changed")),
    )
    monkeypatch.setattr(ingress.os, "close", closed.append)
    with pytest.raises(ingress.RosterSyncError, match="unable to read"):
        ingress._read_local_file(file_path)
    assert closed == [91]

    monkeypatch.undo()
    with pytest.raises(ingress.RosterSyncError, match="real directory"):
        ingress._directory_files(file_path)
    (tmp_path / "one.md").write_text("# One", encoding="utf-8")
    monkeypatch.setattr(ingress, "MAX_DIRECTORY_ENTRIES", 0)
    with pytest.raises(ingress.RosterSyncError, match="exceeds 0 entries"):
        ingress._directory_files(tmp_path)


def test_local_file_detects_post_read_replacement_and_stream_overflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "agent.md"
    path.write_bytes(b"ab")
    actual = path.stat()
    changed_values = list(actual)
    changed_values[6] = actual.st_size + 1
    changed = os.stat_result(changed_values)
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda value: value)
    metadata = iter((actual, changed))
    monkeypatch.setattr(ingress.os, "lstat", lambda _path: next(metadata))
    with pytest.raises(ingress.RosterSyncError, match="changed while being read"):
        ingress._read_local_file(path)

    monkeypatch.undo()
    actual = path.stat()
    reported_small = SimpleNamespace(
        st_mode=actual.st_mode,
        st_dev=actual.st_dev,
        st_ino=actual.st_ino,
        st_file_attributes=getattr(actual, "st_file_attributes", 0),
        st_size=1,
        st_mtime=actual.st_mtime,
        st_mtime_ns=actual.st_mtime_ns,
    )
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda value: value)
    monkeypatch.setattr(ingress, "MAX_LOCAL_FILE_BYTES", 1)
    monkeypatch.setattr(ingress.os, "lstat", lambda _path: reported_small)
    with pytest.raises(ingress.RosterSyncError, match="exceeds 1 bytes"):
        ingress._read_local_file(path)


def test_path_chain_and_directory_discovery_change_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    linked = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
    monkeypatch.setattr(ingress.os, "lstat", lambda _path: linked)
    with pytest.raises(ingress.RosterSyncError, match="symbolic links"):
        ingress._assert_real_path_chain(Path("relative"))

    monkeypatch.undo()
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda path: path)
    fingerprints = iter(((1,), (2,)))
    monkeypatch.setattr(ingress, "_directory_fingerprint", lambda _metadata: next(fingerprints))
    with pytest.raises(ingress.RosterSyncError, match="changed during discovery"):
        ingress._directory_files(tmp_path)

    monkeypatch.undo()
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda path: path)
    fingerprints = iter(((1,), (1,), (2,)))
    monkeypatch.setattr(ingress, "_directory_fingerprint", lambda _metadata: next(fingerprints))
    with pytest.raises(ingress.RosterSyncError, match="changed during discovery"):
        ingress._directory_files(tmp_path)

    monkeypatch.undo()
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda path: path)
    fingerprints = iter(((1,), (1,), (1,), (2,)))
    monkeypatch.setattr(ingress, "_directory_fingerprint", lambda _metadata: next(fingerprints))
    with pytest.raises(ingress.RosterSyncError, match="changed during discovery"):
        ingress._directory_files(tmp_path)

    monkeypatch.undo()
    child = tmp_path / "special.md"
    directory = SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0)
    special = SimpleNamespace(st_mode=stat.S_IFIFO, st_file_attributes=0)
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda path: path)
    monkeypatch.setattr(Path, "iterdir", lambda _path: iter((child,)))
    monkeypatch.setattr(
        ingress.os,
        "lstat",
        lambda path: special if Path(path) == child else directory,
    )
    monkeypatch.setattr(ingress, "_directory_fingerprint", lambda _metadata: (1,))
    with pytest.raises(ingress.RosterSyncError, match="non-regular agent file"):
        ingress._directory_files(tmp_path)

    monkeypatch.undo()
    (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")
    assert ingress._directory_files(tmp_path) == []


def test_read_and_download_source_shape_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingress, "_validate_source_spec", lambda _url: ("http", "url"))
    monkeypatch.setattr(ingress, "_read_http_source", lambda _url: "<html>bad</html>")
    with pytest.raises(ingress.RosterSyncError, match="returned HTML"):
        list(ingress._read_url("url"))

    monkeypatch.setattr(ingress, "_read_url", lambda _url: iter((("origin", "[]"),)))
    monkeypatch.setattr(ingress, "_load_json", lambda *_args: {})
    with pytest.raises(ValueError, match="must be a list"):
        ingress.download_from_source("source")
    monkeypatch.setattr(ingress, "_load_json", lambda *_args: [1])
    with pytest.raises(ValueError, match="not an object"):
        ingress.download_from_source("source")
    monkeypatch.setattr(ingress, "MAX_SOURCE_CANDIDATES", 0)
    monkeypatch.setattr(ingress, "_load_json", lambda *_args: [{}])
    with pytest.raises(ingress.RosterSyncError, match="more than 0 candidates"):
        ingress.download_from_source("source")

    monkeypatch.undo()
    monkeypatch.setattr(ingress, "_read_url", lambda _url: iter((("origin", "# Agent"),)))
    monkeypatch.setattr(ingress, "MAX_SOURCE_CANDIDATES", 0)
    with pytest.raises(ingress.RosterSyncError, match="more than 0 candidates"):
        ingress.download_from_source("source")


def test_read_url_directory_and_special_file_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    assert list(ingress._read_url(str(tmp_path))) == []

    special = SimpleNamespace(st_mode=stat.S_IFIFO)
    monkeypatch.setattr(ingress, "_validate_source_spec", lambda _url: ("path", Path("special")))
    monkeypatch.setattr(ingress, "_assert_real_path_chain", lambda path: path)
    monkeypatch.setattr(ingress.os, "lstat", lambda _path: special)
    with pytest.raises(ingress.RosterSyncError, match="regular file or directory"):
        list(ingress._read_url("special"))


def test_agent_validation_reasons_and_explicit_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = (
        ({"slug": "x", "name": "name", "description": "desc", "prompt_body": "body"}, "slug"),
        ({"slug": "valid", "name": "", "description": "desc", "prompt_body": "body"}, "name"),
        (
            {"slug": "valid", "name": "name", "description": "", "prompt_body": "body"},
            "description",
        ),
        ({"slug": "valid", "name": "name", "description": "desc", "prompt_body": ""}, "prompt"),
    )
    monkeypatch.setattr(ingress, "_normalize_agent", lambda value: value)
    for value, expected in cases:
        ok, reason = ingress.validate_agent(value)
        assert ok is False
        assert expected in reason
    assert ingress.categorize_agent({"categories": ["Security", "security"]}) == ["security"]


class _FakeConnection:
    def __init__(self, row: Any = None, rows: list[Any] | None = None) -> None:
        self.row = row
        self.rows = rows or []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(fetchone=lambda: self.row, fetchall=lambda: self.rows)

    def executemany(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _FakeStore:
    def __init__(self, connection: _FakeConnection | None = None) -> None:
        self.connection = connection or _FakeConnection()

    def _connect(self) -> _FakeConnection:
        return self.connection

    def _uuid(self) -> str:
        return "uuid"

    def get_active_roster(self) -> list[dict[str, Any]]:
        return []


def test_sync_quarantine_and_candidate_id_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_normalize_agent", lambda value: value)
    monkeypatch.setattr(sync, "validate_agent", lambda _value: (False, "bad"))
    with pytest.raises(ValueError, match="invalid agent"):
        sync.quarantine_candidate({"slug": "bad"}, "source", _FakeStore())  # type: ignore[arg-type]

    monkeypatch.setattr(sync, "MAX_SOURCE_CANDIDATES", 0)
    with pytest.raises(ingress.RosterSyncError, match="candidate ids"):
        sync._load_candidate_agents(_FakeStore(), ["candidate"])  # type: ignore[arg-type]

    monkeypatch.setattr(sync, "MAX_SOURCE_CANDIDATES", 10)
    monkeypatch.setattr(sync, "_connect", lambda store: store._connect())
    assert sync._load_candidate_agents(_FakeStore(_FakeConnection(rows=[])), None) == []  # type: ignore[arg-type]
    assert sync._load_candidate_agents(_FakeStore(), []) == []  # type: ignore[arg-type]

    monkeypatch.setattr(sync, "MAX_SOURCE_CANDIDATES", 0)
    with pytest.raises(ingress.RosterSyncError, match="more than 0 candidates"):
        sync._load_candidate_agents(
            _FakeStore(_FakeConnection(rows=[{}])),
            None,  # type: ignore[arg-type]
        )


def test_sync_diff_resource_and_serializability_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sync, "MAX_SOURCE_CANDIDATES", 0)
    monkeypatch.setattr(sync, "_load_candidate_agents", lambda *_args, **_kwargs: [_agent()])
    with pytest.raises(ingress.RosterSyncError, match="limit is 0"):
        sync.create_roster_diff(_FakeStore())  # type: ignore[arg-type]

    monkeypatch.setattr(sync, "MAX_SOURCE_CANDIDATES", 10)
    monkeypatch.setattr(sync, "MAX_TOTAL_SOURCE_BYTES", 0)
    with pytest.raises(ingress.RosterSyncError, match="candidate content"):
        sync.create_roster_diff(_FakeStore())  # type: ignore[arg-type]

    monkeypatch.setattr(sync, "MAX_TOTAL_SOURCE_BYTES", 10_000)
    monkeypatch.setattr(sync, "_active_fingerprint", lambda _active: "0" * 64)
    monkeypatch.setattr(
        sync.json,
        "dumps",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("bad")),
    )
    with pytest.raises(ingress.RosterSyncError, match="not JSON serializable"):
        sync.create_roster_diff(_FakeStore())  # type: ignore[arg-type]


def test_candidate_loading_parse_and_hash_integrity_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = _agent()
    row = {
        **agent,
        "download_hash": agent["hash"],
        "download_status": "quarantined",
    }
    monkeypatch.setattr(
        sync,
        "parse_agent_file",
        lambda _content: (_ for _ in ()).throw(ValueError("invalid")),
    )
    with pytest.raises(ingress.RosterSyncError, match="cannot be parsed"):
        sync._load_candidate_agents(
            _FakeStore(_FakeConnection(rows=[row])),
            None,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(sync, "parse_agent_file", ingress.parse_agent_file)
    bad_candidate_hash = dict(row, hash="wrong")
    with pytest.raises(ingress.RosterSyncError, match="content hash does not match"):
        sync._load_candidate_agents(
            _FakeStore(_FakeConnection(rows=[bad_candidate_hash])),
            None,  # type: ignore[arg-type]
        )
    bad_download_hash = dict(row, download_hash="wrong")
    with pytest.raises(ingress.RosterSyncError, match="quarantined download"):
        sync._load_candidate_agents(
            _FakeStore(_FakeConnection(rows=[bad_download_hash])),
            None,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("value", "agent_count", "message"),
    [
        ([], 0, "must be an object"),
        (
            {"snapshot_id": "other", "approved": False, "candidates": [], "candidate_ids": []},
            0,
            "identity",
        ),
        (
            {"snapshot_id": "s", "approved": "no", "candidates": [], "candidate_ids": []},
            0,
            "approval state",
        ),
        (
            {"snapshot_id": "s", "approved": False, "candidates": {}, "candidate_ids": []},
            0,
            "candidate manifest",
        ),
        (
            {"snapshot_id": "s", "approved": False, "candidates": [], "candidate_ids": []},
            1,
            "agent count",
        ),
    ],
)
def test_snapshot_manifest_shape_validation(value: Any, agent_count: int, message: str) -> None:
    with pytest.raises(ingress.RosterSyncError, match=message):
        sync._snapshot_manifest_lists(value, snapshot_id="s", agent_count=agent_count)


def test_snapshot_manifest_candidate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "MAX_SOURCE_CANDIDATES", 0)
    with pytest.raises(ingress.RosterSyncError, match="limit is 0"):
        sync._snapshot_manifest_lists(
            {
                "snapshot_id": "s",
                "approved": False,
                "candidates": [{}],
                "candidate_ids": [],
            },
            snapshot_id="s",
            agent_count=1,
        )


def test_snapshot_candidate_and_identity_validation_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ingress.RosterSyncError, match="non-object"):
        sync._validated_manifest_candidate([], snapshot_id="s")
    valid = _agent()
    monkeypatch.setattr(sync, "validate_agent", lambda _candidate: (False, "bad"))
    with pytest.raises(ingress.RosterSyncError, match="invalid agent"):
        sync._validated_manifest_candidate(valid, snapshot_id="s")
    monkeypatch.setattr(sync, "validate_agent", ingress.validate_agent)

    tampered = dict(valid)
    tampered["hash"] = "wrong"
    with pytest.raises(ingress.RosterSyncError, match="identity or content hash"):
        sync._validated_manifest_candidate(tampered, snapshot_id="s")
    missing_id = dict(valid)
    missing_id.pop("id")
    with pytest.raises(ingress.RosterSyncError, match="id is missing"):
        sync._validated_manifest_candidate(missing_id, snapshot_id="s")

    monkeypatch.setattr(sync, "MAX_TOTAL_SOURCE_BYTES", 0)
    with pytest.raises(ingress.RosterSyncError, match="candidate content"):
        sync._validated_manifest_candidates([valid], snapshot_id="s")
    with pytest.raises(ingress.RosterSyncError, match="duplicate candidate ids"):
        sync._validate_manifest_candidate_identity(
            [valid, valid], ["same", "same"], ["same", "same"], snapshot_id="s"
        )
    other = dict(valid, id="candidate-2")
    with pytest.raises(ingress.RosterSyncError, match="duplicate agents"):
        sync._validate_manifest_candidate_identity(
            [valid, other], ["one", "two"], ["one", "two"], snapshot_id="s"
        )
    with pytest.raises(ingress.RosterSyncError, match="active basis"):
        sync._validate_manifest_active_basis({"active_basis": "invalid"}, "s")


def test_snapshot_read_candidate_record_and_serialization_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(KeyError, match="snapshot not found"):
        sync._snapshot_from_connection(_FakeConnection(None), "missing")

    for row, message in (
        ({"manifest": "{}", "agent_count": True, "activated": 0}, "agent count"),
        ({"manifest": "{}", "agent_count": 0, "activated": True}, "activation state"),
    ):
        monkeypatch.setattr(sync, "_load_json", lambda *_args: {})
        with pytest.raises(ingress.RosterSyncError, match=message):
            sync._snapshot_from_connection(_FakeConnection(row), "s")

    candidate = _agent()
    monkeypatch.setattr(sync, "_candidate_records", lambda *_args: {})
    with pytest.raises(ingress.RosterSyncError, match="records are missing"):
        sync._assert_candidate_records(
            _FakeConnection(), [candidate], allowed_statuses=frozenset({"pending"})
        )

    def record_for(candidate: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        record = {
            **candidate,
            "status": "pending",
            "download_status": "quarantined",
            "download_content": candidate["content"],
            "download_hash": ingress._hash_text(candidate["content"]),
            **{field: json.dumps(candidate.get(field, [])) for field in ingress._LIST_FIELDS},
        }
        record.update(overrides)
        return record

    monkeypatch.setattr(
        sync,
        "_candidate_records",
        lambda *_args: {candidate["id"]: record_for(candidate, status="rejected")},
    )
    with pytest.raises(ingress.RosterSyncError, match="allowed state"):
        sync._assert_candidate_records(
            _FakeConnection(), [candidate], allowed_statuses=frozenset({"pending"})
        )
    monkeypatch.setattr(
        sync,
        "_candidate_records",
        lambda *_args: {candidate["id"]: record_for(candidate, name="changed")},
    )
    with pytest.raises(ingress.RosterSyncError, match="no longer matches quarantine"):
        sync._assert_candidate_records(
            _FakeConnection(), [candidate], allowed_statuses=frozenset({"pending"})
        )
    monkeypatch.setattr(
        sync,
        "_candidate_records",
        lambda *_args: {candidate["id"]: record_for(candidate, categories=json.dumps(["changed"]))},
    )
    with pytest.raises(ingress.RosterSyncError, match="no longer matches quarantine"):
        sync._assert_candidate_records(
            _FakeConnection(), [candidate], allowed_statuses=frozenset({"pending"})
        )

    monkeypatch.setattr(
        sync.json,
        "dumps",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RecursionError()),
    )
    with pytest.raises(ingress.RosterSyncError, match="not JSON serializable"):
        sync._serialized_manifest({})
    monkeypatch.undo()
    monkeypatch.setattr(sync, "MAX_SNAPSHOT_MANIFEST_BYTES", 0)
    with pytest.raises(ingress.RosterSyncError, match="limit is 0"):
        sync._serialized_manifest({})


@pytest.mark.parametrize(
    ("function", "manifest", "message"),
    [
        (sync.approve_snapshot, ({"approved": False, "candidates": []}, True), "already activated"),
        (sync.approve_snapshot, ({"approved": False, "candidates": []}, False), "no agents"),
        (
            sync.activate_snapshot,
            ({"approved": False, "candidates": []}, False),
            "must be approved",
        ),
        (sync.activate_snapshot, ({"approved": True, "candidates": []}, False), "no agents"),
    ],
)
def test_snapshot_lifecycle_refuses_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
    function: Any,
    manifest: tuple[dict[str, Any], bool],
    message: str,
) -> None:
    connection = _FakeConnection()
    store = _FakeStore(connection)
    monkeypatch.setattr(sync, "_snapshot_from_connection", lambda *_args: manifest)
    with pytest.raises(ingress.RosterSyncError, match=message):
        function(store, "s")  # type: ignore[arg-type]
    assert connection.rolled_back is True
    assert connection.closed is True


def test_approve_already_approved_snapshot_commits_without_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection()
    store = _FakeStore(connection)
    manifest = {"approved": True, "candidates": [_agent()]}
    monkeypatch.setattr(sync, "_snapshot_from_connection", lambda *_args: (manifest, False))
    monkeypatch.setattr(sync, "_assert_candidate_records", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(sync, "assert_candidate_audits_current", lambda *_args, **_kwargs: None)
    sync.approve_snapshot(store, "s")  # type: ignore[arg-type]
    assert connection.committed is True
    assert connection.closed is True
