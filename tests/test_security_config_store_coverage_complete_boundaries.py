from __future__ import annotations

import ctypes
import importlib
import io
import json
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from agency_runtime.adapters.claude import wrapper as claude_wrapper
from agency_runtime.adapters.codex import wrapper as codex_wrapper
from agency_runtime.adapters.generic import wrapper as generic_wrapper
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw import node_bridge
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core import bounded_io, bounded_json, bounded_yaml, config, windows_acl


class _Metadata:
    def __init__(
        self,
        *,
        mode: int = stat.S_IFREG | 0o600,
        size: int = 1,
        device: int = 1,
        inode: int = 1,
        attributes: int = 0,
    ) -> None:
        self.st_mode = mode
        self.st_size = size
        self.st_dev = device
        self.st_ino = inode
        self.st_file_attributes = attributes


class _FakePath:
    def __init__(self, metadata: _Metadata) -> None:
        self.metadata = metadata

    def lstat(self) -> _Metadata:
        return self.metadata


@pytest.mark.parametrize(
    ("opened", "error_type"),
    [
        (_Metadata(mode=stat.S_IFDIR | 0o700), bounded_io.UnsafeFileError),
        (_Metadata(inode=2), bounded_io.UnsafeFileError),
        (_Metadata(size=3), bounded_io.FileSizeLimitError),
    ],
)
def test_bounded_file_revalidates_after_open_and_closes_descriptor(
    monkeypatch: pytest.MonkeyPatch,
    opened: _Metadata,
    error_type: type[Exception],
) -> None:
    closed: list[int] = []
    monkeypatch.setattr(bounded_io.os, "open", lambda *_args: 71)
    monkeypatch.setattr(bounded_io.os, "fstat", lambda _descriptor: opened)
    monkeypatch.setattr(bounded_io.os, "close", closed.append)

    with pytest.raises(error_type):
        bounded_io.read_bounded_regular_file(
            _FakePath(_Metadata()),  # type: ignore[arg-type]
            limit=2,
            label="state",
        )

    assert closed == [71]


def test_bounded_file_detects_windows_reparse_attributes() -> None:
    assert bounded_io._is_link_or_reparse(_Metadata(attributes=0x400)) is True  # type: ignore[arg-type]


def test_bounded_file_detects_stream_growth_after_safe_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Stream:
        def __enter__(self) -> Stream:
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self, _size: int) -> bytes:
            return b"ab"

    metadata = _Metadata(size=1)
    monkeypatch.setattr(bounded_io.os, "open", lambda *_args: 72)
    monkeypatch.setattr(bounded_io.os, "fstat", lambda _descriptor: metadata)
    monkeypatch.setattr(bounded_io.os, "fdopen", lambda *_args: Stream())
    with pytest.raises(bounded_io.FileSizeLimitError, match="size limit"):
        bounded_io.read_bounded_regular_file(
            _FakePath(metadata),  # type: ignore[arg-type]
            limit=1,
            label="state",
        )


def test_bounded_json_defensive_validation_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(bounded_json.BoundedJSONError, match="input-byte"):
        bounded_json.safe_load_bounded_json(b"{}", maximum_bytes=1)
    with pytest.raises(bounded_json.BoundedJSONError, match="UTF-8"):
        bounded_json.safe_load_bounded_json(b"\xff")
    with pytest.raises(bounded_json.BoundedJSONError, match="valid Unicode"):
        bounded_json.safe_load_bounded_json('"\ud800"')
    with pytest.raises(bounded_json.BoundedJSONError, match="nesting-depth"):
        bounded_json._validate({"nested": 1}, maximum_depth=0, maximum_nodes=10)
    with pytest.raises(bounded_json.BoundedJSONError, match="non-finite"):
        bounded_json._validate(float("nan"), maximum_depth=1, maximum_nodes=10)
    with pytest.raises(bounded_json.BoundedJSONError, match="unsupported value type"):
        bounded_json._validate(object(), maximum_depth=1, maximum_nodes=10)

    monkeypatch.setattr(
        bounded_json.json,
        "loads",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RecursionError()),
    )
    with pytest.raises(bounded_json.BoundedJSONError, match="not valid bounded data"):
        bounded_json.safe_load_bounded_json("{}")


def test_bounded_yaml_defensive_validation_branches() -> None:
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="input-byte"):
        bounded_yaml.safe_load_bounded(b"{}", maximum_bytes=1)
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="input-byte"):
        bounded_yaml.safe_load_bounded("é", maximum_bytes=1)
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="input-byte"):
        bounded_yaml.safe_load_bounded("xx", maximum_bytes=1)
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="UTF-8"):
        bounded_yaml.safe_load_bounded(b"\xff")
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="valid Unicode"):
        bounded_yaml.safe_load_bounded("\ud800")
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="hashable"):
        bounded_yaml.safe_load_bounded("? [a, b]\n: value\n")
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="mapping keys must be text"):
        bounded_yaml._validate({1: "value"}, maximum_depth=2, maximum_nodes=10)

    with pytest.raises(bounded_yaml.BoundedYAMLError, match="structural-node"):
        bounded_yaml._validate([1], maximum_depth=2, maximum_nodes=1)
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="nesting-depth"):
        bounded_yaml._validate([1], maximum_depth=0, maximum_nodes=10)
    shared_mapping: dict[str, Any] = {}
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="cycle or shared"):
        bounded_yaml._validate(
            {"first": shared_mapping, "second": shared_mapping},
            maximum_depth=3,
            maximum_nodes=10,
        )

    shared: list[str] = []
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="cycle or shared"):
        bounded_yaml._validate(
            {"first": shared, "second": shared}, maximum_depth=3, maximum_nodes=10
        )
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="non-finite"):
        bounded_yaml._validate(float("inf"), maximum_depth=1, maximum_nodes=10)
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="unsupported value type"):
        bounded_yaml._validate(object(), maximum_depth=1, maximum_nodes=10)
    with pytest.raises(bounded_yaml.BoundedYAMLError, match="not valid bounded data"):
        bounded_yaml.safe_load_bounded("[unterminated")


class _Callable:
    def __init__(self, function: Any) -> None:
        self.function = function
        self.argtypes: Any = None
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.function(*args)


def _token_libraries(*, opens: bool, restricted: bool, closed: list[Any]) -> tuple[Any, Any]:
    advapi = SimpleNamespace(
        OpenProcessToken=_Callable(lambda *_args: opens),
        IsTokenRestricted=_Callable(lambda _token: restricted),
    )
    kernel = SimpleNamespace(
        GetCurrentProcess=_Callable(lambda: 123),
        CloseHandle=_Callable(lambda token: closed.append(token) or True),
    )
    return advapi, kernel


@pytest.mark.parametrize(("restricted", "expected"), [(False, False), (True, True)])
def test_windows_token_probe_success_closes_handle(
    monkeypatch: pytest.MonkeyPatch,
    restricted: bool,
    expected: bool,
) -> None:
    closed: list[Any] = []
    advapi, kernel = _token_libraries(opens=True, restricted=restricted, closed=closed)
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )

    assert windows_acl.current_process_token_is_restricted(is_windows=True) is expected
    assert len(closed) == 1


def test_windows_token_probe_failure_is_distinct_from_unrestricted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert windows_acl.current_process_token_is_restricted(is_windows=False) is False
    advapi, kernel = _token_libraries(opens=False, restricted=False, closed=[])
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    with pytest.raises(windows_acl.WindowsTokenProbeError):
        windows_acl.current_process_token_is_restricted(is_windows=True)

    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("missing API")),
        raising=False,
    )
    with pytest.raises(windows_acl.WindowsTokenProbeError):
        windows_acl.current_process_token_is_restricted(is_windows=True)


def _acl_libraries(*, get_code: int, entries_code: int, set_code: int) -> tuple[Any, Any]:
    def get_security(*args: Any) -> int:
        if get_code == 0:
            args[3]._obj.value = 101
            args[-1]._obj.value = 102
        return get_code

    def set_entries(*args: Any) -> int:
        if entries_code == 0:
            args[-1]._obj.value = 103
        return entries_code

    advapi = SimpleNamespace(
        GetNamedSecurityInfoW=_Callable(get_security),
        SetEntriesInAclW=_Callable(set_entries),
        SetNamedSecurityInfoW=_Callable(lambda *_args: set_code),
    )
    kernel = SimpleNamespace(LocalFree=_Callable(lambda _pointer: None))
    return advapi, kernel


@pytest.mark.parametrize(
    ("get_code", "entries_code", "set_code", "expected"),
    [(5, 0, 0, False), (0, 5, 0, False), (0, 0, 5, False), (0, 0, 0, True)],
)
def test_owner_acl_native_result_paths(
    monkeypatch: pytest.MonkeyPatch,
    get_code: int,
    entries_code: int,
    set_code: int,
    expected: bool,
) -> None:
    advapi, kernel = _acl_libraries(get_code=get_code, entries_code=entries_code, set_code=set_code)
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    assert windows_acl._apply_owner_only_acl(Path("config"), directory=True) is expected


def test_owner_acl_native_exceptions_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
        raising=False,
    )
    assert windows_acl._apply_owner_only_acl(Path("config"), directory=False) is False

    error = windows_acl.WindowsTokenProbeError("probe")
    with pytest.raises(windows_acl.WindowsTokenProbeError) as raised:
        windows_acl.restrict_windows_acl(
            Path("config"),
            is_windows=True,
            token_restriction_probe=lambda: (_ for _ in ()).throw(error),
        )
    assert raised.value is error


def _sddl_libraries(
    *,
    get_code: int,
    convert_ok: bool,
    sddl_text: str,
    freed: list[Any],
) -> tuple[Any, Any, Any]:
    buffer = ctypes.create_unicode_buffer(sddl_text)

    def get_security(*args: Any) -> int:
        if get_code == 0:
            args[-1]._obj.value = 101
        return get_code

    def convert(*args: Any) -> bool:
        if convert_ok:
            args[-2]._obj.value = ctypes.addressof(buffer)
            args[-1]._obj.value = len(sddl_text) + 1
        return convert_ok

    advapi = SimpleNamespace(
        GetNamedSecurityInfoW=_Callable(get_security),
        ConvertSecurityDescriptorToStringSecurityDescriptorW=_Callable(convert),
    )
    kernel = SimpleNamespace(LocalFree=_Callable(lambda pointer: freed.append(pointer) or None))
    return advapi, kernel, buffer


@pytest.mark.parametrize(
    ("get_code", "convert_ok", "expected", "free_count"),
    [(5, True, "", 0), (0, False, "", 1), (0, True, "owner-only", 2)],
)
def test_windows_sddl_read_result_paths(
    monkeypatch: pytest.MonkeyPatch,
    get_code: int,
    convert_ok: bool,
    expected: str,
    free_count: int,
) -> None:
    freed: list[Any] = []
    advapi, kernel, buffer = _sddl_libraries(
        get_code=get_code,
        convert_ok=convert_ok,
        sddl_text="owner-only",
        freed=freed,
    )
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )

    assert windows_acl._read_windows_sddl(Path("state")) == expected
    assert len(freed) == free_count
    assert buffer.value == "owner-only"


def test_windows_sddl_read_native_exception_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
        raising=False,
    )
    assert windows_acl._read_windows_sddl(Path("state")) == ""


def test_config_low_level_error_and_transport_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("JUDGE_KEY", "judge")
    monkeypatch.setenv("ADAPTER_KEY", "adapter")
    assert config.ProviderEntry(type="cli").auth_method() == "oauth"
    assert config.ProviderEntry().auth_method() == "none"
    assert config.JudgeConfig(api_key_env="JUDGE_KEY").resolve_api_key() == "judge"
    assert config.AdapterEntryConfig(api_key_env="ADAPTER_KEY").resolve_api_key() == "adapter"
    assert config.AdapterEntryConfig().resolve_api_key() == ""
    assert config._is_loopback_http_url("http://user@127.0.0.1") is False
    assert config._is_loopback_http_url("http://localhost") is True
    assert config.is_safe_credential_url("ftp://127.0.0.1") is False

    missing = tmp_path / "missing.yaml"
    assert config._load_yaml(missing) == {}
    monkeypatch.setattr(
        config,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(bounded_io.FileSizeLimitError("large")),
    )
    with pytest.raises(ValueError, match="1 MiB"):
        config._load_yaml(missing)
    monkeypatch.setattr(
        config,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unsafe")),
    )
    with pytest.raises(ValueError, match="unavailable or unsafe"):
        config._load_yaml(missing)
    monkeypatch.setattr(config, "read_bounded_regular_file", lambda *_args, **_kwargs: b"{}")
    monkeypatch.setattr(
        config,
        "safe_load_bounded",
        lambda _text: (_ for _ in ()).throw(bounded_yaml.BoundedYAMLError("bad yaml")),
    )
    with pytest.raises(ValueError, match="bad yaml"):
        config._load_yaml(missing)

    with pytest.raises(ValueError, match="at most 4"):
        config._build_providers([{}] * 5)
    assert config._dict_to_config({"observability": []}).observability.retention_days == 30


class _StoreStub:
    def get_skills_for_session(self, session_id: str) -> list[str]:
        return [f"skill:{session_id}"]

    def get_specialists_for_session(self, session_id: str) -> list[str]:
        return [f"specialist:{session_id}"]

    def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
        return []


class _BackendStub:
    result: ClassVar[dict[str, Any]] = {"status": "ok"}
    calls: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"constructor": self.kwargs, "execute": kwargs})
        return dict(self.result)


def test_cli_adapter_wrappers_cover_availability_prompts_and_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = _StoreStub()
    monkeypatch.setattr(claude_wrapper.shutil, "which", lambda _name: "claude")
    monkeypatch.setattr(codex_wrapper.shutil, "which", lambda _name: "codex")
    monkeypatch.setattr(generic_wrapper.shutil, "which", lambda _name: "generic")
    monkeypatch.setattr(claude_wrapper, "ClaudeExecBackend", _BackendStub)
    monkeypatch.setattr(codex_wrapper, "CodexExecBackend", _BackendStub)
    monkeypatch.setattr(generic_wrapper, "GenericCLIBackend", _BackendStub)

    claude = claude_wrapper.ClaudeAdapter(store=store)  # type: ignore[arg-type]
    codex = codex_wrapper.CodexAdapter(store=store)  # type: ignore[arg-type]
    generic = generic_wrapper.GenericAdapter(store=store, cli_cmd="generic")  # type: ignore[arg-type]
    assert claude.is_available() and codex.is_available() and generic.is_available()
    assert claude.report_skills_loaded("s") == ["skill:s"]
    assert claude.report_specialists_loaded("s") == ["specialist:s"]
    assert claude.get_delegate_backend() == "claude_exec"
    assert claude.expose_model_telemetry("s") == {}
    assert codex.report_skills_loaded("s") == ["skill:s"]
    assert codex.report_specialists_loaded("s") == ["specialist:s"]
    assert codex.get_delegate_backend() == "codex_exec"
    assert codex.expose_model_telemetry("s") == {}
    assert generic.report_skills_loaded("s") == ["skill:s"]
    assert generic.report_specialists_loaded("s") == ["specialist:s"]
    assert generic.get_delegate_backend() == "generic_command"
    assert generic.expose_model_telemetry("s") == {}
    assert generic_wrapper.GenericAdapter(store=store).is_available() is False  # type: ignore[arg-type]
    assert claude.exec("task", str(tmp_path), "specialist")["status"] == "ok"
    assert codex.exec("task", str(tmp_path), "specialist")["status"] == "ok"
    assert generic.exec("task", ["--safe"], str(tmp_path))["status"] == "ok"

    import agency_runtime.core.selector.pipeline as pipeline

    monkeypatch.setattr(pipeline, "is_trivial", lambda _message: True)
    assert codex.run_preflight("s", "hi") is None
    monkeypatch.setattr(pipeline, "is_trivial", lambda _message: False)
    monkeypatch.setattr(pipeline, "route_and_build_context", lambda *_args, **_kwargs: "ctx")
    assert codex.run_preflight("s", "complex") == {"context": "ctx"}
    monkeypatch.setattr(pipeline, "route_and_build_context", lambda *_args, **_kwargs: "")
    assert codex.run_preflight("s", "complex") is None

    _BackendStub.result = {"status": "unavailable"}
    assert claude.exec("task", str(tmp_path))["status"] == "unavailable"
    _BackendStub.result = {"status": "ok"}


def test_plugin_import_surfaces_and_store_reports() -> None:
    plugin = importlib.import_module("agency_runtime.adapters.generic.plugin")
    assert plugin.GenericAdapter is generic_wrapper.GenericAdapter
    store = _StoreStub()
    for adapter in (
        HermesAdapter(store=store),  # type: ignore[arg-type]
        OpenClawAdapter(store=store),  # type: ignore[arg-type]
    ):
        assert adapter.report_skills_loaded("s") == ["skill:s"]
        assert adapter.report_specialists_loaded("s") == ["specialist:s"]
        assert adapter.expose_model_telemetry("s") == {}
    assert HermesAdapter(store=store).get_delegate_backend() == "delegate_task"  # type: ignore[arg-type]
    assert OpenClawAdapter(store=store).get_delegate_backend() == "sessions_spawn"  # type: ignore[arg-type]
    openclaw = OpenClawAdapter(store=store)  # type: ignore[arg-type]
    openclaw.apply_finalization = lambda *_args, **_kwargs: "final"  # type: ignore[method-assign]
    assert openclaw.on_response_finalizing("draft") == "final"


def test_openclaw_bridge_hostile_payload_and_finalization_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert node_bridge._attempt_number({"attempt": True}) == 0
    assert node_bridge._attempt_number({"attempt": object()}) == 0
    assert node_bridge.handle([]) == {"error": "payload must be an object"}  # type: ignore[arg-type]

    monkeypatch.setattr(
        node_bridge.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(b"x" * (node_bridge.MAX_INPUT_BYTES + 1))),
    )
    assert node_bridge._read_payload()["error"] == "hook payload exceeds 1 MiB"
    monkeypatch.setattr(
        node_bridge.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(json.dumps([]).encode())),
    )
    assert node_bridge._read_payload()["error"] == "payload must be an object"

    class Store:
        def record_finalization(self, **_kwargs: Any) -> None:
            raise RuntimeError("database unavailable")

    class Adapter:
        store = Store()

        def pre_llm_call_handler(self, **_kwargs: Any) -> dict[str, Any]:
            return {"context": "ok"}

        def pre_verify_handler(self, **_kwargs: Any) -> dict[str, Any]:
            return {"action": "continue"}

        def runtime_enabled(self) -> bool:
            return True

        def post_tool_call_handler(self, **_kwargs: Any) -> None:
            return None

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", Adapter)
    assert node_bridge.handle({"action": "preflight", "userMessage": "   "}) == {}
    assert node_bridge.handle({"action": "pre_verify", "finalResponse": ""}) == {}
    assert node_bridge.handle(
        {
            "action": "pre_verify",
            "finalResponse": "answer",
            "traceId": "trace",
            "attempt": "2",
        }
    ) == {"action": "continue"}
    assert node_bridge.handle({"action": "pre_verify", "finalResponse": "answer"}) == {
        "action": "continue"
    }
    assert node_bridge.handle({"action": "post_tool_call", "toolInput": "invalid"}) == {}
    assert node_bridge.handle({"action": "unknown"}) == {"error": "unknown action: unknown"}
