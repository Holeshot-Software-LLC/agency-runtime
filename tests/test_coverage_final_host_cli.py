"""Final behavioral branch closure for host bridges, CLI, and runtime files."""

from __future__ import annotations

import argparse
import io
import json
import stat
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime import _bootstrap
from agency_runtime.adapters import base as base_module
from agency_runtime.adapters import hooks
from agency_runtime.adapters.hermes import bridge as hermes_bridge
from agency_runtime.adapters.litellm import callback as litellm_callback
from agency_runtime.adapters.litellm import request_context
from agency_runtime.adapters.openclaw import node_bridge
from agency_runtime.cli import _common, delegation_commands, install_commands, service_commands
from agency_runtime.core import (
    bounded_io,
    configuration_identity,
    configuration_persistence,
    dashboard_runtime,
    dashboard_service_core,
    dashboard_service_inspection,
)
from agency_runtime.core import config as config_module


def _stat_result(
    mode: int,
    *,
    inode: int = 7,
    device: int = 3,
    links: int = 1,
    uid: int = 1000,
    size: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        st_mode=mode,
        st_ino=inode,
        st_dev=device,
        st_nlink=links,
        st_uid=uid,
        st_size=size,
        st_file_attributes=0,
    )


def _raise(error: Exception) -> Any:
    raise error


def test_isolated_bootstrap_rejects_bad_modules_and_dispatches(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["bootstrap"])
    assert _bootstrap.main() == 2
    assert "rejected" in capsys.readouterr().err

    monkeypatch.setattr(sys, "argv", ["bootstrap", "not.allowed"])
    assert _bootstrap.main() == 2
    assert "rejected" in capsys.readouterr().err

    package_parent = str(Path(_bootstrap.__file__).resolve().parent.parent)
    monkeypatch.setattr(sys, "path", [package_parent, "elsewhere", package_parent])
    monkeypatch.setattr(sys, "argv", ["bootstrap", "agency_runtime.cli", "status"])
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        _bootstrap.runpy,
        "run_module",
        lambda module, **kwargs: captured.update(module=module, kwargs=kwargs, argv=list(sys.argv)),
    )
    assert _bootstrap.main() == 0
    assert captured == {
        "module": "agency_runtime.cli",
        "kwargs": {"run_name": "__main__", "alter_sys": True},
        "argv": ["agency_runtime.cli", "status"],
    }
    assert sys.path[0] == package_parent
    assert sys.path.count(package_parent) == 1


def test_isolated_bootstrap_configures_available_text_streams(monkeypatch) -> None:
    calls: list[dict[str, str]] = []
    stream = SimpleNamespace(reconfigure=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(_bootstrap.sys, "stdin", SimpleNamespace())
    monkeypatch.setattr(_bootstrap.sys, "stdout", stream)
    monkeypatch.setattr(_bootstrap.sys, "stderr", stream)

    _bootstrap._configure_utf8_stdio()

    assert calls == [
        {"encoding": "utf-8", "errors": "strict"},
        {"encoding": "utf-8", "errors": "strict"},
    ]


class _Adapter(base_module.BaseAdapter):
    host_name = "test"

    def is_available(self) -> bool:
        return True

    def get_delegate_backend(self) -> str | None:
        return None


def test_base_projects_native_run_and_ignores_unresolved_receipt(monkeypatch) -> None:
    projected = base_module._native_delegation_batch(
        "delegate_task",
        {"tasks": [None, {"goal": "review"}]},
        {
            "delegation_id": "native-1",
            "results": [{"task_index": 1, "status": "completed"}],
        },
    )
    assert projected == [
        (
            {"goal": "review"},
            {"task_index": 1, "status": "completed", "native_run_id": "native-1"},
        )
    ]

    adapter = _Adapter(store=SimpleNamespace(get_host_control=lambda _host: {"enabled": True}))
    monkeypatch.setattr(adapter, "resolve_turn_trace", lambda *_args: "")
    adapter.post_api_request_handler(session_id="session", trace_id="trace")


def test_hermes_bridge_input_config_and_adapter_boundaries(monkeypatch, tmp_path) -> None:
    assert hermes_bridge._bounded_text("éé", maximum_bytes=3) == "é"
    with pytest.raises(Exception, match="byte limit"):
        hermes_bridge._read_payload(io.BytesIO(b"x" * (hermes_bridge.MAX_INPUT_BYTES + 1)))
    with pytest.raises(Exception, match="must be an object"):
        hermes_bridge._read_payload(io.BytesIO(b"[]"))
    assert hermes_bridge._read_payload(io.BytesIO(b'{"action":"x"}')) == {"action": "x"}

    assert hermes_bridge._config_path(()) is None
    with pytest.raises(ValueError, match="accepts only"):
        hermes_bridge._config_path(("--other", "x"))
    with pytest.raises(ValueError, match="absolute"):
        hermes_bridge._config_path(("--config", "relative.yaml"))
    config_path = tmp_path / "agency.yaml"
    monkeypatch.setattr(hermes_bridge, "resolve_config_path", lambda value, **_kw: value)
    assert hermes_bridge._config_path(("--config", str(config_path))) == config_path

    cfg = SimpleNamespace(
        config_path=str(config_path),
        store=SimpleNamespace(resolved_path=lambda: tmp_path / "agency.db"),
    )
    stores: list[tuple[Any, Any]] = []
    monkeypatch.setattr(hermes_bridge, "load_config", lambda *args, **kwargs: cfg)
    monkeypatch.setattr(
        hermes_bridge,
        "Store",
        lambda path=None, config_path=None: stores.append((path, config_path)) or "store",
    )
    monkeypatch.setattr(hermes_bridge, "HermesAdapter", lambda store: ("adapter", store))
    assert hermes_bridge._adapter(config_path) == ("adapter", "store")
    assert hermes_bridge._adapter(None) == ("adapter", "store")
    assert stores == [
        (None, str(config_path)),
        (None, str(config_path)),
    ]
    assert hermes_bridge._attempt_number(object()) == 1


def test_hermes_bridge_dispatch_and_fail_closed_paths(monkeypatch) -> None:
    monkeypatch.setattr("agency_runtime.core.runtime_control.master_enabled", lambda: False)
    with pytest.raises(ValueError, match="unknown"):
        hermes_bridge.handle({"action": "unknown"})

    calls: list[tuple[str, Any]] = []
    store = SimpleNamespace(close_turn_evidence=lambda *args, **kw: calls.append(("close", kw)))
    adapter = SimpleNamespace(
        store=store,
        post_tool_call_handler=lambda **kw: calls.append(("tool", kw)),
        post_api_request_handler=lambda **kw: calls.append(("api", kw)),
        pre_verify_handler=lambda **_kw: None,
        apply_finalization=lambda *_args, **_kw: "",
        resolve_turn_trace=lambda *_args: _raise(OSError("offline")),
    )
    monkeypatch.setattr("agency_runtime.core.runtime_control.master_enabled", lambda: True)

    assert hermes_bridge._pre_verify(adapter, {}) is None
    assert hermes_bridge._transform_output(adapter, {}) == hermes_bridge.FINALIZATION_BLOCK_RESPONSE
    hermes_bridge._close_session(adapter, {})
    assert calls == []
    assert not hermes_bridge._terminalize_policy_rejection(adapter, "x", "s", "t", "m")

    assert (
        hermes_bridge.handle(
            {"action": "post_tool_call", "args": "bad", "tool_name": "tool"}, adapter=adapter
        )
        is None
    )
    assert calls[-1][0] == "tool" and calls[-1][1]["args"] == {}
    assert (
        hermes_bridge.handle(
            {"action": "post_api_request", "payload": {"model": "m"}}, adapter=adapter
        )
        is None
    )
    assert calls[-1] == ("api", {"model": "m", "session_id": "", "trace_id": ""})

    monkeypatch.setattr(
        hermes_bridge,
        "handle_host_control_command",
        lambda *args, **kw: {"message": f"{args[0]}:{kw['source']}"},
    )
    assert hermes_bridge.handle({"action": "control"}, adapter=adapter) == "hermes:hermes-command"
    with pytest.raises(ValueError, match="unknown"):
        hermes_bridge.handle({"action": "unknown"}, adapter=adapter)


def test_hermes_bridge_encoding_and_main(monkeypatch, capsys) -> None:
    monkeypatch.setattr(hermes_bridge, "MAX_OUTPUT_BYTES", 8)
    with pytest.raises(ValueError, match="byte limit"):
        hermes_bridge._encode_result("too long")

    class _BinarySink:
        def __init__(self) -> None:
            self.buffer = io.BytesIO()

    sink = _BinarySink()
    monkeypatch.setattr(hermes_bridge.sys, "stdout", sink)
    monkeypatch.setattr(hermes_bridge, "MAX_OUTPUT_BYTES", 1024)
    monkeypatch.setattr(hermes_bridge, "_read_payload", lambda: {"action": "x"})
    monkeypatch.setattr(hermes_bridge, "handle", lambda *_args, **_kw: "ok")
    assert hermes_bridge.main([]) == 0
    assert json.loads(sink.buffer.getvalue()) == {"ok": True, "result": "ok"}

    sink = _BinarySink()
    monkeypatch.setattr(hermes_bridge.sys, "stdout", sink)
    monkeypatch.setattr(hermes_bridge, "_read_payload", lambda: _raise(ValueError("bad")))
    assert hermes_bridge.main([]) == 2
    assert json.loads(sink.buffer.getvalue())["ok"] is False
    assert "ValueError" in capsys.readouterr().err


def test_hook_lazy_store_task_resolution_and_work_unit_injection(monkeypatch) -> None:
    created = object()
    monkeypatch.setattr(hooks, "Store", lambda *args, **kwargs: created)
    bridge = hooks.HookBridge("codex", adapter=SimpleNamespace())
    assert bridge.store is created

    assert (
        bridge._resolve_codex_task_name(
            tool_name="spawn_agent", tool_input={}, session_id="s", trace_id="t"
        )
        == ""
    )
    bridge.store = SimpleNamespace(get_delegations=lambda _trace: _raise(OSError("offline")))
    assert (
        bridge._resolve_codex_task_name(
            tool_name="spawn_agent",
            tool_input={"task_name": "agency-unit-test"},
            session_id="s",
            trace_id="t",
        )
        == ""
    )
    bridge.store = SimpleNamespace(
        get_delegations=lambda _trace: [],
        get_completion_evidence_snapshot=lambda *_args: _raise(OSError("offline")),
    )
    assert (
        bridge._resolve_codex_task_name(
            tool_name="spawn_agent",
            tool_input={"task_name": "agency-unit-test"},
            session_id="s",
            trace_id="t",
        )
        == ""
    )

    observed: dict[str, Any] = {}
    bridge = hooks.HookBridge(
        "codex",
        store=SimpleNamespace(),
        adapter=SimpleNamespace(post_tool_call_handler=lambda **kw: observed.update(kw)),
    )
    monkeypatch.setattr(
        bridge,
        "_correlation",
        lambda *_args: hooks.HookCorrelation("session", "trace", "unit-9", "model", "tool"),
    )
    monkeypatch.setattr(bridge, "_resolve_codex_task_name", lambda **_kw: "")
    bridge.handle(
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "unknown",
            "tool_input": {},
            "tool_response": "done",
        }
    )
    assert observed["args"]["work_unit_id"] == "unit-9"


def test_hook_stdio_constructs_explicit_store(monkeypatch) -> None:
    created: list[tuple[Any, Any]] = []
    store = object()
    monkeypatch.setattr(
        hooks,
        "Store",
        lambda db_path=None, config_path=None: created.append((db_path, config_path)) or store,
    )
    monkeypatch.setattr(hooks.HookBridge, "handle", lambda self, payload: {})
    output = io.BytesIO()
    assert (
        hooks.run_hook_stdio(
            "codex",
            db_path="db.sqlite",
            config_path="agency.yaml",
            input_stream=io.BytesIO(b'{"hook_event_name":"Stop"}'),
            output_stream=output,
        )
        == 0
    )
    assert created == [("db.sqlite", "agency.yaml")]


def test_litellm_lazy_store_master_off_and_request_context(monkeypatch) -> None:
    cfg = config_module.AgencyConfig(
        store=config_module.StoreConfig("runtime.db"),
        config_path="agency.yaml",
    )
    monkeypatch.setattr(litellm_callback, "config_for_store", lambda *_args: cfg)
    stores: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        litellm_callback,
        "Store",
        lambda path=None, config_path=None: stores.append((path, config_path)) or "store",
    )
    adapter = litellm_callback.LiteLLMAdapter()
    assert adapter.store == "store"
    adapter.store = "replacement"
    assert adapter.store == "replacement"
    assert stores == [(None, "agency.yaml")]

    monkeypatch.setattr("agency_runtime.core.runtime_control.master_enabled", lambda: False)
    registration = litellm_callback.register_litellm_callback(config=cfg)
    assert not registration.registered and "master switch" in registration.reason
    assert litellm_callback.litellm_proxy_callback_config(cfg) == {
        "litellm_settings": {"turn_off_message_logging": True}
    }

    assert not request_context._owned_agency_context(
        "[AGENCY PREFLIGHT] Specialist routing suggestion without header"
    )
    values, found = request_context._strip_agency_blocks(
        [
            "plain",
            7,
            {"type": "image", "content": "opaque"},
            {"type": "text", "text": object()},
        ]
    )
    assert values[0:3] == ["plain", 7, {"type": "image", "content": "opaque"}]
    assert values[3]["type"] == "text" and found is False
    marker = object()
    assert request_context._strip_agency_system_content(marker) == (marker, False)
    assert request_context.inject_message_context([7, {"role": "user"}], "context") == [
        {"role": "system", "content": "context"},
        7,
        {"role": "user"},
    ]
    payload: dict[str, Any] = {"prompt": ""}
    request_context._append_string_context(payload, "prompt", "")
    assert payload == {"prompt": ""}
    request_context._append_string_context(payload, "prompt", "context")
    assert payload == {"prompt": "context"}
    monkeypatch.setattr(request_context, "_strip_agency_suffix", lambda _value: ("", True))
    assert request_context._strip_agency_blocks(["owned"]) == ([], True)
    monkeypatch.setattr(request_context, "_strip_agency_suffix", lambda _value: ("user", True))
    payload = {"prompt": "owned"}
    request_context._append_string_context(payload, "prompt", "")
    assert payload == {"prompt": "user"}
    assert request_context._strip_completion_context(
        "[AGENCY PREFLIGHT] Specialist routing suggestion no complete header"
    ).endswith("no complete header")


def test_small_cli_store_delegation_and_service_branches(monkeypatch, capsys) -> None:
    cfg = config_module.AgencyConfig(
        store=config_module.StoreConfig("runtime.db"),
        config_path="",
    )
    created: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        _common,
        "Store",
        lambda path=None, config_path=None: created.append((path, config_path)) or object(),
    )
    _common.store(cfg)
    assert created == [(Path("runtime.db"), None)]
    _common.store(replace(cfg, config_path="agency.yaml"))
    assert created[-1] == (Path("runtime.db"), "agency.yaml")

    result = {"bypassed": True, "exit_code": 0}
    assert delegation_commands._emit_delegate_result(argparse.Namespace(json=False), result) == 0
    assert "globally disabled" in capsys.readouterr().out

    stores: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        service_commands,
        "Store",
        lambda db=None, config_path=None: stores.append((db, config_path)) or object(),
    )
    assert service_commands._configured_store(argparse.Namespace(db=None, config=None)) is None
    assert (
        service_commands._configured_store(argparse.Namespace(db="db", config="config")) is not None
    )
    assert service_commands._configured_store(argparse.Namespace(db="db", config=None)) is not None
    assert stores == [("db", "config"), ("db", None)]


def test_install_control_rendering_and_failure_paths(monkeypatch, capsys) -> None:
    error = install_commands._failed_control_result("codex", ValueError(""))
    assert error["error"] == "ValueError"
    install_commands._print_global_control_result(error)
    install_commands._print_global_control_result({"ok": True, "enabled": True, "dry_run": True})
    install_commands._print_global_control_result(
        {"ok": True, "enabled": False, "dry_run": False, "transport": "dashboard"}
    )
    output = capsys.readouterr().out
    assert "ValueError" in output
    assert "DRY RUN" in output
    assert "globally disabled" in output

    args = SimpleNamespace(global_control=True, json=False)
    monkeypatch.setattr(
        install_commands,
        "_global_control_result",
        lambda *_args, **_kw: _raise(RuntimeError("broker down")),
    )
    dependencies = install_commands.InstallDependencies(
        load_config=lambda: config_module.AgencyConfig(),
        store_factory=lambda _cfg: object(),
        emit_json=lambda _payload: None,
        readiness_probe=lambda: True,
    )
    assert install_commands._cmd_host_control(args, enabled=True, dependencies=dependencies) == 1
    assert "broker down" in capsys.readouterr().out

    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: _raise(RuntimeError("blocked")),
    )
    monkeypatch.setattr("agency_runtime.core.runtime_control.master_enabled", lambda: True)
    monkeypatch.setattr(
        "agency_runtime.core.host_control.inspect_all_host_statuses", lambda *_args, **_kw: []
    )
    monkeypatch.setattr(
        install_commands,
        "_direct_inference_snapshot",
        lambda _store, _dependencies: {
            "schema_version": "agency.dashboard.inference_operations.v1",
            "configured": False,
            "required_for_eligible_turns": False,
            "state": "not_configured",
            "evidence": ("configuration readiness plus recent persisted routing/model receipts"),
            "provider_chain": [],
            "latest_model_resolution": None,
            "recent_failures": [],
            "failure_count": 0,
            "failures_truncated": False,
        },
    )
    status_args = SimpleNamespace(agent=None, json=True)
    emitted: list[Any] = []
    dependencies = replace(dependencies, emit_json=emitted.append)
    assert install_commands.cmd_status(status_args, dependencies=dependencies) == 0
    assert emitted[-1]["master_transport"] == "fail-enabled"
    assert emitted[-1]["master"]["diagnostic_error"] == "blocked"


def test_install_preflight_human_error_and_per_host_exception(monkeypatch, capsys) -> None:
    cfg = config_module.AgencyConfig()
    dependencies = install_commands.InstallDependencies(
        load_config=lambda: cfg,
        store_factory=lambda _cfg: object(),
        emit_json=lambda _payload: None,
        readiness_probe=lambda: True,
    )
    args = SimpleNamespace(
        all=False,
        agent=None,
        backup=None,
        dry_run=False,
        execute=False,
        json=False,
        no_dashboard=False,
        profile=None,
        rollback=False,
    )
    monkeypatch.setattr(
        install_commands, "dashboard_service_environment_overrides", lambda _cfg: ("X",)
    )
    monkeypatch.setattr(install_commands, "resolve_config_path", lambda: Path("agency.yaml"))
    monkeypatch.setattr("agency_runtime.core.installer.detect_installed_agents", lambda: [])
    monkeypatch.setattr("agency_runtime.core.installer.plan_agent_adapter", lambda *_args: {})
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_service.plan_dashboard_service",
        lambda **_kw: {"ok": False, "error": "unsafe env"},
    )
    monkeypatch.setattr("agency_runtime.core.installer.install_agent_adapter", lambda *_args: {})
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_service.install_dashboard_service", lambda **_kw: {}
    )
    monkeypatch.setattr(
        "agency_runtime.core.installer.rollback_agent_adapter", lambda *_args, **_kw: {}
    )
    assert install_commands.cmd_install(args, dependencies=dependencies) == 1
    assert "unsafe env" in capsys.readouterr().out

    control_args = SimpleNamespace(
        global_control=False,
        agent="codex",
        all=False,
        dry_run=False,
        native=True,
        json=False,
    )
    monkeypatch.setattr(
        "agency_runtime.core.installer.toggle_agency",
        lambda *_args, **_kw: _raise(OSError("no")),
    )
    assert (
        install_commands._cmd_host_control(control_args, enabled=True, dependencies=dependencies)
        == 1
    )
    assert "no" in capsys.readouterr().out


def test_install_master_control_broker_double_failure(monkeypatch) -> None:
    from agency_runtime.core import runtime_control

    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        lambda: _raise(runtime_control.RuntimeControlSecurityError("direct unavailable")),
    )
    monkeypatch.setattr(
        runtime_control,
        "_restricted_windows_control_target",
        lambda _path: True,
    )
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_api_request",
        lambda *_args, **_kw: _raise(OSError("dashboard unavailable")),
    )
    with pytest.raises(RuntimeError, match="dashboard service could not broker"):
        install_commands._read_master_control_with_broker()


def test_config_rejects_credential_transports_file_types_and_nonmapping_overlay(
    monkeypatch, tmp_path
) -> None:
    provider = config_module.ProviderEntry(
        name="remote", base_url="http://example.test", api_key="secret"
    )
    with pytest.raises(ValueError, match="provider 'remote'"):
        config_module._enforce_credential_transport_constraints(
            config_module.AgencyConfig(providers=(provider,))
        )

    judge = config_module.JudgeConfig(base_url="http://example.test", api_key="secret")
    with pytest.raises(ValueError, match="judge credentials"):
        config_module._enforce_credential_transport_constraints(
            config_module.AgencyConfig(judge=judge)
        )

    litellm = replace(
        config_module.AdaptersConfig().litellm,
        base_url="http://example.test",
        api_key="secret",
    )
    with pytest.raises(ValueError, match="LiteLLM"):
        config_module._enforce_credential_transport_constraints(
            config_module.AgencyConfig(
                adapters=replace(config_module.AdaptersConfig(), litellm=litellm)
            )
        )

    directory = tmp_path / "not-a-file"
    directory.mkdir()
    with pytest.raises(ValueError, match="regular non-link"):
        config_module._config_file_signature(directory)

    config_path = tmp_path / "agency.yaml"
    defaults_path = tmp_path / "defaults.yaml"
    monkeypatch.setattr(config_module, "_BUNDLED_DEFAULTS", defaults_path)
    monkeypatch.setattr(config_module, "resolve_config_path", lambda value, **_kw: Path(value))
    monkeypatch.setattr(
        config_module,
        "_load_yaml",
        lambda path: {"judge": {}} if Path(path) == defaults_path else {"judge": False},
    )
    monkeypatch.setattr(
        "agency_runtime.core.configuration_schema.validate_config_document", lambda value: value
    )
    with pytest.raises(ValueError, match="judge must be a mapping"):
        config_module._load_config_uncached(config_path)


def test_configuration_identity_rejects_unreadable_parent_and_foreign_manifest(monkeypatch) -> None:
    monkeypatch.setattr(
        configuration_identity.os,
        "lstat",
        lambda _path: _raise(OSError("denied")),
    )
    with pytest.raises(Exception, match="identity could not be validated"):
        configuration_identity._assert_config_identity_link_safe(Path("C:/safe/agency.yaml"))

    candidates = iter(
        [
            _stat_result(stat.S_IFDIR | 0o700),
            _stat_result(stat.S_IFREG | 0o600),
        ]
    )
    monkeypatch.setattr(configuration_identity.os, "lstat", lambda _path: next(candidates))
    with pytest.raises(Exception, match="parent must be a directory"):
        configuration_identity._assert_config_identity_link_safe(Path("C:/safe/agency.yaml"))

    assert not configuration_identity._real_manifest_parent(
        Path("C:/home"), Path("C:/other/manifest.json")
    )


def test_configuration_namespace_acl_and_identity_failures(monkeypatch, tmp_path) -> None:
    subject = configuration_persistence
    monkeypatch.delattr(subject.os, "getxattr", raising=False)
    assert not subject._posix_directory_has_default_acl(tmp_path)
    monkeypatch.setattr(subject.os, "getxattr", lambda *_args, **_kw: b"acl", raising=False)
    assert subject._posix_directory_has_default_acl(tmp_path)
    failure = OSError("unexpected")
    failure.errno = 12345
    monkeypatch.setattr(
        subject.os, "getxattr", lambda *_args, **_kw: _raise(failure), raising=False
    )
    assert subject._posix_directory_has_default_acl(tmp_path)

    path = tmp_path / "config" / "agency.yaml"
    monkeypatch.setattr(subject, "private_path_authority_covers", lambda _path: True)
    assert subject.config_namespace_is_trusted(path, is_windows=True)

    monkeypatch.setattr(subject, "private_path_authority_covers", lambda _path: False)
    monkeypatch.setattr(subject, "_directory_chain", lambda _path: (tmp_path,))
    monkeypatch.setattr(subject.os, "lstat", lambda _path: _raise(OSError("denied")))
    assert not subject.config_namespace_is_trusted(path, is_windows=False)
    monkeypatch.setattr(subject.os, "lstat", lambda _path: _stat_result(stat.S_IFREG | 0o600))
    assert not subject.config_namespace_is_trusted(path, is_windows=False)
    monkeypatch.setattr(subject, "_directory_chain", lambda _path: ())
    assert not subject.config_namespace_is_trusted(path, is_windows=False)


def test_effective_posix_uid_uses_only_the_windows_simulation_fallback(
    monkeypatch,
    os_facade,
) -> None:
    subject = configuration_persistence
    real_os = subject.os
    metadata = SimpleNamespace(st_uid=4242)
    monkeypatch.setattr(
        subject,
        "os",
        os_facade(real_os, name="nt", missing=frozenset({"geteuid"})),
    )
    assert subject._effective_posix_uid(metadata) == 4242

    monkeypatch.setattr(
        subject,
        "os",
        os_facade(real_os, name="posix", missing=frozenset({"geteuid"})),
    )
    assert subject._effective_posix_uid(metadata) is None


def test_configuration_namespace_probe_owner_and_private_file_failures(
    monkeypatch, tmp_path
) -> None:
    subject = configuration_persistence
    path = tmp_path / "config" / "agency.yaml"
    directory = _stat_result(stat.S_IFDIR | 0o700, uid=1000)
    monkeypatch.setattr(subject, "_directory_chain", lambda _path: (tmp_path,))
    monkeypatch.setattr(subject.os, "lstat", lambda _path: directory)
    assert not subject.config_namespace_is_trusted(
        path,
        is_windows=True,
        windows_acl_probe=lambda *_args: _raise(OSError("probe")),
    )
    monkeypatch.setattr(subject, "_effective_posix_uid", lambda _metadata: None)
    assert not subject.config_namespace_is_trusted(path, is_windows=False)
    assert not subject.config_namespace_is_trusted(path, is_windows=False, effective_uid=2000)

    regular = _stat_result(stat.S_IFREG | 0o600, links=2, uid=1000)
    monkeypatch.setattr(subject.os, "lstat", lambda _path: regular)
    with pytest.raises(Exception, match="one regular non-link"):
        subject._ensure_config_file_private(
            path, path_check=lambda _path: False, restrict=lambda *_args, **_kw: True
        )

    regular.st_nlink = 1
    with pytest.raises(Exception, match="owned by the current user"):
        subject._ensure_config_file_private(
            path,
            path_check=lambda _path: False,
            restrict=lambda *_args, **_kw: True,
            is_windows=False,
        )


def test_configuration_parent_post_create_swap_and_lock_handle_security(
    monkeypatch, tmp_path
) -> None:
    subject = configuration_persistence
    path = tmp_path / "config" / "agency.yaml"
    checks = iter((False, True))
    monkeypatch.setattr(subject, "assert_config_namespace", lambda *_args, **_kw: None)
    with pytest.raises(Exception, match="directory symlink"):
        subject.ensure_config_parent(
            path,
            path_check=lambda _path: next(checks),
            restrict=lambda *_args, **_kw: True,
        )

    file_path = tmp_path / "lock"
    file_path.write_bytes(b"x")
    with file_path.open("r+b") as handle:
        monkeypatch.setattr(
            subject.os,
            "fstat",
            lambda _fd: _stat_result(stat.S_IFREG | 0o600, links=2, uid=1000, size=1),
        )
        with pytest.raises(Exception, match="multiple links"):
            subject._prepare_config_lock_handle(
                handle,
                lock_path=file_path,
                path_check=lambda _path: False,
                restrict=lambda *_args, **_kw: True,
                windows=True,
            )

        monkeypatch.setattr(
            subject.os,
            "fstat",
            lambda _fd: _stat_result(stat.S_IFREG | 0o600, links=1, uid=2000, size=1),
        )
        monkeypatch.setattr(subject, "_effective_posix_uid", lambda _metadata: 1000)
        with pytest.raises(Exception, match="owned by the current user"):
            subject._prepare_config_lock_handle(
                handle,
                lock_path=file_path,
                path_check=lambda _path: False,
                restrict=lambda *_args, **_kw: True,
                windows=False,
            )


def test_atomic_config_write_closes_unpublished_descriptor(monkeypatch, tmp_path) -> None:
    subject = configuration_persistence
    path = tmp_path / "agency.yaml"
    monkeypatch.setattr(subject, "assert_config_namespace", lambda *_args, **_kw: None)
    monkeypatch.setattr(subject, "_ensure_config_file_private", lambda *_args, **_kw: True)
    closed: list[int] = []
    real_close = subject.os.close
    monkeypatch.setattr(
        subject.os,
        "close",
        lambda fd: (closed.append(fd), real_close(fd))[1],
    )
    with pytest.raises(RuntimeError, match="stop before fdopen"):
        subject.atomic_write_yaml(
            path,
            {"profile": "standard"},
            ensure_parent=lambda target: target.parent.mkdir(exist_ok=True),
            restrict=lambda *_args, **_kw: _raise(RuntimeError("stop before fdopen")),
            preflight=lambda _path: None,
            path_check=lambda _path: False,
            is_windows=True,
        )
    assert closed


def test_bounded_permission_repair_normalizes_open_and_post_repair_failures(
    monkeypatch, tmp_path, os_facade
) -> None:
    monkeypatch.setattr(
        bounded_io,
        "os",
        os_facade(bounded_io.os, name="posix", fchmod=lambda *_args: None),
    )
    path = tmp_path / "private"
    regular = _stat_result(stat.S_IFREG | 0o600)
    monkeypatch.setattr(bounded_io.os, "lstat", lambda _path: regular)
    monkeypatch.setattr(bounded_io.os, "open", lambda *_args: _raise(OSError("denied")))
    with pytest.raises(bounded_io.UnsafeFileError, match="opened safely"):
        bounded_io.restrict_posix_path_permissions(path, directory=False)

    directory = _stat_result(stat.S_IFDIR | 0o700)
    monkeypatch.setattr(bounded_io.os, "lstat", lambda _path: directory)
    with pytest.raises(bounded_io.UnsafeFileError, match="opened safely"):
        bounded_io.restrict_posix_path_permissions(path, directory=True)

    calls = 0

    def changing_lstat(_path):
        nonlocal calls
        calls += 1
        if calls == 1:
            return regular
        raise OSError("replaced")

    monkeypatch.setattr(bounded_io.os, "lstat", changing_lstat)
    monkeypatch.setattr(bounded_io.os, "open", lambda *_args: 41)
    monkeypatch.setattr(bounded_io.os, "fstat", lambda _fd: regular)
    monkeypatch.setattr(bounded_io.os, "close", lambda _fd: None)
    with pytest.raises(bounded_io.UnsafeFileError, match="changed after repair"):
        bounded_io.restrict_posix_path_permissions(path, directory=False)

    before = _stat_result(stat.S_IFREG | 0o600, inode=1)
    replaced = _stat_result(stat.S_IFREG | 0o600, inode=2)
    lstat_values = iter((before, replaced))
    monkeypatch.setattr(bounded_io.os, "lstat", lambda _path: next(lstat_values))
    monkeypatch.setattr(bounded_io.os, "open", lambda *_args: 42)
    monkeypatch.setattr(bounded_io.os, "fstat", lambda _fd: before)
    with pytest.raises(bounded_io.UnsafeFileError, match="changed after repair"):
        bounded_io.restrict_posix_path_permissions(path, directory=False)


def test_dashboard_service_secret_names_and_environment_plan(monkeypatch, tmp_path) -> None:
    secret = SimpleNamespace(api_key_env="GOOD_SECRET")
    invalid = SimpleNamespace(api_key_env="bad-name")
    config = SimpleNamespace(
        judge=secret,
        providers=(invalid, secret),
        adapters=SimpleNamespace(
            litellm=secret,
            hermes=None,
            openclaw=None,
            codex=None,
            claude=None,
        ),
    )
    assert dashboard_service_core._configured_secret_environment_names(config) == {"GOOD_SECRET"}
    assert dashboard_service_core._configured_secret_environment_names(None) == set()

    context = SimpleNamespace(manager="systemd", config_path=tmp_path / "agency.yaml")
    monkeypatch.setattr(dashboard_service_inspection, "_context", lambda **_kw: context)
    monkeypatch.setattr(dashboard_service_inspection, "load_config", lambda *_args, **_kw: config)
    monkeypatch.setattr(
        dashboard_service_inspection,
        "dashboard_service_environment_overrides",
        lambda _config: ("AGENCY_CONFIG",),
    )
    monkeypatch.setattr(
        dashboard_service_inspection,
        "dashboard_service_environment_error",
        lambda values: f"non-durable: {','.join(values)}",
    )
    monkeypatch.setattr(
        dashboard_service_inspection,
        "_failed",
        lambda action, ctx, **kw: {"ok": False, "action": action, "manager": ctx.manager, **kw},
    )
    result = dashboard_service_inspection.plan_dashboard_service(
        home_dir=tmp_path, platform_name="linux"
    )
    assert result["dry_run"] is True
    assert result["non_durable_environment_overrides"] == ["AGENCY_CONFIG"]


def test_openclaw_terminal_recovery_and_acceptance_validation() -> None:
    missing_finder = SimpleNamespace(
        store=SimpleNamespace(get_open_traces_for_session=lambda _session: [])
    )
    with pytest.raises(RuntimeError, match="cannot be verified"):
        node_bridge._recover_exact_terminal_trace(missing_finder, "s", "draft")

    with pytest.raises(RuntimeError, match="could not be verified"):
        node_bridge._accept_exact_finalized_response(
            SimpleNamespace(store=SimpleNamespace()), "s", "t", "draft"
        )
    with pytest.raises(RuntimeError, match="terminal response evidence is inconsistent"):
        node_bridge._accept_exact_finalized_response(
            SimpleNamespace(
                store=SimpleNamespace(get_authoritative_finalization=lambda *_args, **_kw: "bad")
            ),
            "s",
            "t",
            "draft",
        )

    legacy_with_policy_hash = SimpleNamespace(
        store=SimpleNamespace(
            get_open_traces_for_session=lambda _session: [],
            find_authoritative_trace_by_policy_hash=lambda *_args, **_kw: None,
            find_authoritative_trace=lambda *_args, **_kw: "legacy",
            get_authoritative_finalization=lambda *_args, **_kw: {
                "policy_response_hash": "already-bound"
            },
        )
    )
    assert node_bridge._recover_exact_terminal_trace(legacy_with_policy_hash, "s", "draft") == ""


def test_openclaw_finish_commit_and_outbound_state_fail_closed(monkeypatch) -> None:
    common = {
        "adapter": SimpleNamespace(),
        "decision": {"action": "continue", "evidence_revision": 1},
        "final_response": "draft",
        "session_id": "s",
        "trace_id": "t",
    }
    monkeypatch.setattr(node_bridge, "_commit_terminal_outcome", lambda *_args, **_kw: False)
    assert node_bridge._finish_exhausted_retry(**common)["action"] == "continue"

    assert (
        node_bridge._exact_outbound_terminal_state(
            SimpleNamespace(store=SimpleNamespace()),
            session_id="s",
            trace_id="t",
            digest="d",
        )
        == ""
    )
    assert (
        node_bridge._exact_outbound_terminal_state(
            SimpleNamespace(
                store=SimpleNamespace(
                    get_authoritative_finalization=lambda *_args, **_kw: _raise(OSError("offline"))
                )
            ),
            session_id="s",
            trace_id="t",
            digest="d",
        )
        == "unavailable"
    )


@pytest.mark.parametrize("payload", ["not-json", "[]"])
def test_openclaw_outbound_payload_rejects_invalid_json_shapes(payload) -> None:
    assert not node_bridge._outbound_binding_matches_policy_text(payload, "draft")


def test_openclaw_outbound_gate_error_and_decision_matrix(monkeypatch) -> None:
    common = {"session_id": "s", "trace_id": "t", "final_response": "draft"}
    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(runtime_enabled=lambda: _raise(OSError("control")), store=object()),
        **common,
    )
    assert result["action"] == "replace" and "soft-control" in result["message"]

    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(runtime_enabled=lambda: True, store=object()),
        outbound_payload=json.dumps({"text": "different"}),
        **common,
    )
    assert result["action"] == "replace" and "bind" in result["message"]

    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(runtime_enabled=lambda: True, store=object()),
        session_id="",
        trace_id="t",
        final_response="draft",
    )
    assert result["action"] == "replace" and "correlate" in result["message"]

    monkeypatch.setattr(
        node_bridge,
        "_recover_exact_terminal_trace",
        lambda *_args, **_kw: _raise(OSError("correlation")),
    )
    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(runtime_enabled=lambda: True, store=object()),
        session_id="s",
        trace_id="",
        final_response="draft",
    )
    assert result["action"] == "replace" and "correlate" in result["message"]

    monkeypatch.setattr(
        node_bridge, "_exact_outbound_terminal_state", lambda *_args, **_kw: "unavailable"
    )
    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(runtime_enabled=lambda: True, store=object()), **common
    )
    assert "authoritative" in result["message"]

    monkeypatch.setattr(node_bridge, "_exact_outbound_terminal_state", lambda *_args, **_kw: "")
    monkeypatch.setattr(
        node_bridge,
        "_safe_policy_decision",
        lambda *_args, **_kw: {"runtime_disabled": True},
    )
    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(runtime_enabled=lambda: True, store=object()), **common
    )
    assert result["runtimeDisabled"] is True

    monkeypatch.setattr(
        node_bridge,
        "_safe_policy_decision",
        lambda *_args, **_kw: {"action": "accept", "evidence_revision": 0},
    )
    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(runtime_enabled=lambda: True, store=object()), **common
    )
    assert result["action"] == "replace" and "bind outbound" in result["message"]


def test_openclaw_persistence_runtime_disabled_and_constructor_matrix(monkeypatch) -> None:
    decision = {"action": "continue", "evidence_revision": 0}
    assert (
        node_bridge._persist_continuation_decision(
            SimpleNamespace(),
            decision,
            final_response="draft",
            session_id="s",
            attempt=0,
            trace_id="t",
        )["action"]
        == "continue"
    )

    monkeypatch.setattr("agency_runtime.core.runtime_control.master_enabled", lambda: False)
    disabled_outbound = node_bridge._runtime_disabled_result(
        {"outboundPayload": "", "finalResponse": "draft"}, "outbound_gate"
    )
    assert disabled_outbound["runtimeDisabled"] is True and disabled_outbound["bypassed"] is True
    assert node_bridge._runtime_disabled_result({}, "preflight")["runtimeEnabled"] is False
    assert node_bridge._runtime_disabled_result({}, "post_tool_call") == {}
    assert "unknown action" in node_bridge._runtime_disabled_result({}, "unknown")["error"]

    class BrokenAdapter:
        def __init__(self) -> None:
            raise OSError("offline")

    monkeypatch.setattr("agency_runtime.core.runtime_control.master_enabled", lambda: True)
    monkeypatch.setattr(node_bridge, "OpenClawAdapter", BrokenAdapter)
    assert (
        node_bridge.handle({"action": "pre_verify", "finalResponse": "draft"})["action"]
        == "continue"
    )

    adapter = SimpleNamespace(runtime_enabled=lambda: False, store=object())
    assert node_bridge.handle({"action": "preflight", "userMessage": "work"}, adapter=adapter) == {
        "runtimeEnabled": False
    }


def test_openclaw_main_reports_payload_error(monkeypatch) -> None:
    monkeypatch.setattr(node_bridge, "_read_payload", lambda: {"error": "bad input"})
    output = io.StringIO()
    monkeypatch.setattr(node_bridge.sys, "stdout", output)
    assert node_bridge.main([]) == 2
    assert json.loads(output.getvalue()) == {"error": "bad input"}


def test_dashboard_directory_chain_rejects_links_changes_and_unreadable_entries(
    monkeypatch,
) -> None:
    path = Path("C:/runtime")
    monkeypatch.setattr(dashboard_runtime, "_directory_candidates", lambda _path: (path,))
    monkeypatch.setattr(
        dashboard_runtime.os,
        "lstat",
        lambda _path: _stat_result(stat.S_IFREG | 0o600),
    )
    with pytest.raises(OSError, match="real directories"):
        dashboard_runtime._directory_snapshot(path)
    with pytest.raises(OSError, match="real directories"):
        dashboard_runtime._inspect_existing_directory_chain(path)

    expected = _stat_result(stat.S_IFDIR | 0o700, inode=1)
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: _raise(OSError("gone")))
    with pytest.raises(OSError, match="changed during operation"):
        dashboard_runtime._validate_directory_snapshot(((path, expected),))
    monkeypatch.setattr(
        dashboard_runtime.os,
        "lstat",
        lambda _path: _stat_result(stat.S_IFDIR | 0o700, inode=2),
    )
    with pytest.raises(OSError, match="changed during operation"):
        dashboard_runtime._validate_directory_snapshot(((path, expected),))


def test_dashboard_lock_rejects_existing_special_file_and_open_failure(monkeypatch) -> None:
    path = Path("C:/runtime/.dashboard.lock")
    monkeypatch.setattr(
        dashboard_runtime.os,
        "lstat",
        lambda _path: _stat_result(stat.S_IFDIR | 0o700),
    )
    with pytest.raises(OSError, match="regular non-link"):
        dashboard_runtime._open_runtime_lock(path, ())

    monkeypatch.setattr(
        dashboard_runtime.os,
        "lstat",
        lambda _path: _raise(FileNotFoundError()),
    )
    monkeypatch.setattr(
        dashboard_runtime.os,
        "open",
        lambda *_args, **_kw: _raise(OSError("denied")),
    )
    with pytest.raises(OSError, match="opened safely"):
        dashboard_runtime._open_runtime_lock(path, ())


def test_dashboard_lock_detects_open_and_initialization_swaps(
    monkeypatch,
    os_facade,
) -> None:
    path = Path("C:/runtime/.dashboard.lock")
    regular = _stat_result(stat.S_IFREG | 0o600, inode=1)
    replaced = _stat_result(stat.S_IFREG | 0o600, inode=2)
    calls = 0
    monkeypatch.setattr(
        dashboard_runtime,
        "os",
        os_facade(dashboard_runtime.os, name="nt"),
    )

    def lstat_during_open(_path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise FileNotFoundError
        return replaced

    closed: list[int] = []
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lstat_during_open)
    monkeypatch.setattr(dashboard_runtime.os, "open", lambda *_args, **_kw: 9)
    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: regular)
    monkeypatch.setattr(dashboard_runtime.os, "close", closed.append)
    with pytest.raises(OSError, match="changed while it was opened"):
        dashboard_runtime._open_runtime_lock(path, ())
    assert closed == [9]

    calls = 0

    def lstat_before_init(_path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise FileNotFoundError
        return regular if calls == 2 else replaced

    closed.clear()
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lstat_before_init)
    monkeypatch.setattr(dashboard_runtime, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(dashboard_runtime, "restrict_private_file", lambda _path: True)
    with pytest.raises(OSError, match="changed before initialization"):
        dashboard_runtime._open_runtime_lock(path, ())
    assert closed == [9]


def test_dashboard_lock_and_temporary_descriptor_reject_unsafe_permissions(
    monkeypatch,
    os_facade,
) -> None:
    path = Path("C:/runtime/.dashboard.lock")
    secure = _stat_result(stat.S_IFREG | 0o600, inode=1)
    unsafe = _stat_result(stat.S_IFREG | 0o644, inode=1)
    replaced = _stat_result(stat.S_IFREG | 0o600, inode=2)
    lstat_calls = 0

    def lstat(_path):
        nonlocal lstat_calls
        lstat_calls += 1
        if lstat_calls == 1:
            raise FileNotFoundError
        return secure

    fstat_values = iter((secure, unsafe))
    monkeypatch.setattr(
        dashboard_runtime,
        "os",
        os_facade(dashboard_runtime.os, name="posix"),
    )
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lstat)
    monkeypatch.setattr(dashboard_runtime.os, "open", lambda *_args, **_kw: 10)
    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: next(fstat_values))
    monkeypatch.setattr(
        dashboard_runtime.os,
        "fchmod",
        lambda *_args: None,
        raising=False,
    )
    monkeypatch.setattr(dashboard_runtime.os, "close", lambda _fd: None)
    monkeypatch.setattr(dashboard_runtime, "_validate_directory_snapshot", lambda _snapshot: None)
    with pytest.raises(OSError, match="permissions are unsafe"):
        dashboard_runtime._open_runtime_lock(path, ())

    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: secure)
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: replaced)
    with pytest.raises(OSError, match="changed during creation"):
        dashboard_runtime._secure_temporary_descriptor(path, 11)

    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: secure)
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: secure)
    fstat_values = iter((secure, unsafe))
    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: next(fstat_values))
    with pytest.raises(OSError, match="permissions are unsafe"):
        dashboard_runtime._secure_temporary_descriptor(path, 11)


def test_dashboard_temporary_descriptor_detects_post_permission_swap(
    monkeypatch,
    os_facade,
) -> None:
    path = Path("C:/runtime/temp")
    secure = _stat_result(stat.S_IFREG | 0o600, inode=1)
    replaced = _stat_result(stat.S_IFREG | 0o600, inode=2)
    lstat_values = iter((secure, replaced))
    monkeypatch.setattr(
        dashboard_runtime,
        "os",
        os_facade(dashboard_runtime.os, name="posix"),
    )
    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: secure)
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: next(lstat_values))
    monkeypatch.setattr(
        dashboard_runtime.os,
        "fchmod",
        lambda *_args: None,
        raising=False,
    )
    with pytest.raises(OSError, match="changed before serialization"):
        dashboard_runtime._secure_temporary_descriptor(path, 11)


def test_dashboard_runtime_lock_detects_swap_before_acquisition(
    monkeypatch,
    os_facade,
) -> None:
    regular = _stat_result(stat.S_IFREG | 0o600, inode=1, size=1)
    replaced = _stat_result(stat.S_IFREG | 0o600, inode=2, size=1)

    class Handle:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def fileno(self):
            return 12

        def seek(self, _offset):
            return None

    monkeypatch.setattr(dashboard_runtime, "_prepare_runtime_parent", lambda _target: ())
    monkeypatch.setattr(dashboard_runtime, "_open_runtime_lock", lambda *_args: Handle())
    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: regular)
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: replaced)
    monkeypatch.setattr(
        dashboard_runtime,
        "os",
        os_facade(dashboard_runtime.os, name="nt"),
    )
    fake_msvcrt = SimpleNamespace(
        LK_NBLCK=1,
        LK_UNLCK=2,
        locking=lambda *_args: None,
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    with (
        pytest.raises(OSError, match="changed before acquisition"),
        dashboard_runtime._runtime_lock(Path("C:/runtime/dashboard.json")),
    ):
        pytest.fail("lock should not be yielded")


def test_dashboard_publish_rejects_parent_identity_change(monkeypatch) -> None:
    expected = ((Path("C:/old"), _stat_result(stat.S_IFDIR | 0o700)),)
    current = ((Path("C:/new"), _stat_result(stat.S_IFDIR | 0o700)),)
    monkeypatch.setattr(dashboard_runtime, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(dashboard_runtime, "_prepare_runtime_parent", lambda _target: current)
    with pytest.raises(OSError, match="identity changed after locking"):
        dashboard_runtime._publish_dashboard_runtime(
            Path("C:/runtime/dashboard.json"),
            {},
            expected_directory_snapshot=expected,
        )


def test_dashboard_publish_detects_serialization_and_publication_swaps(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "dashboard.json"
    expected = _stat_result(stat.S_IFREG | 0o600, inode=1)
    replaced = _stat_result(stat.S_IFREG | 0o600, inode=2)
    monkeypatch.setattr(dashboard_runtime, "_prepare_runtime_parent", lambda _target: ())
    monkeypatch.setattr(dashboard_runtime, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(dashboard_runtime, "_assert_replaceable_runtime_file", lambda _path: None)
    monkeypatch.setattr(
        dashboard_runtime,
        "_secure_temporary_descriptor",
        lambda _path, _descriptor: expected,
    )
    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: replaced)
    with pytest.raises(OSError, match="changed during serialization"):
        dashboard_runtime._publish_dashboard_runtime(target, {"ok": True})

    monkeypatch.setattr(dashboard_runtime.os, "fstat", lambda _fd: expected)
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: replaced)
    with pytest.raises(OSError, match="changed before publication"):
        dashboard_runtime._publish_dashboard_runtime(target, {"ok": True})

    lstat_values = iter((expected, replaced))
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: next(lstat_values))
    with pytest.raises(OSError, match="changed during publication"):
        dashboard_runtime._publish_dashboard_runtime(target, {"ok": True})


def test_dashboard_replaceable_file_and_removal_identity_guards(monkeypatch, tmp_path) -> None:
    target = tmp_path / "dashboard.json"
    monkeypatch.setattr(
        dashboard_runtime.os,
        "lstat",
        lambda _path: _stat_result(stat.S_IFDIR | 0o700),
    )
    with pytest.raises(OSError, match="regular non-link"):
        dashboard_runtime._assert_replaceable_runtime_file(target)

    class Lock:
        def __enter__(self):
            return ()

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(dashboard_runtime, "_runtime_lock", lambda _target: Lock())
    monkeypatch.setattr(dashboard_runtime, "_validate_directory_snapshot", lambda _snapshot: None)
    assert not dashboard_runtime.remove_dashboard_runtime(token="x" * 32, pid=1, path=target)

    first = _stat_result(stat.S_IFREG | 0o600, inode=1)
    second = _stat_result(stat.S_IFREG | 0o600, inode=2)
    values = iter((first, second))
    monkeypatch.setattr(dashboard_runtime.os, "lstat", lambda _path: next(values))
    monkeypatch.setattr(
        dashboard_runtime,
        "read_dashboard_runtime",
        lambda **_kw: {"pid": 1, "token": "x" * 32},
    )
    assert not dashboard_runtime.remove_dashboard_runtime(token="x" * 32, pid=1, path=target)


class _DashboardResponse:
    def __init__(self, raw: bytes, *, status: int = 200) -> None:
        self.raw = raw
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _limit: int) -> bytes:
        return self.raw


def _dashboard_descriptor() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pid": 1,
        "port": 7800,
        "token": "x" * 32,
        "started_at": "now",
    }


def test_dashboard_control_api_validates_request_contract() -> None:
    descriptor = _dashboard_descriptor()
    with pytest.raises(ValueError, match="unsupported"):
        dashboard_runtime.dashboard_api_request("/bad", descriptor=descriptor)
    with pytest.raises(ValueError, match="method"):
        dashboard_runtime.dashboard_api_request(
            "/api/runtime", method="DELETE", descriptor=descriptor
        )
    with pytest.raises(ValueError, match="cannot include"):
        dashboard_runtime.dashboard_api_request("/api/runtime", payload={}, descriptor=descriptor)
    with pytest.raises(ValueError, match="require a JSON object"):
        dashboard_runtime.dashboard_api_request(
            "/api/runtime/toggle", method="POST", payload=None, descriptor=descriptor
        )


def test_dashboard_control_api_handles_sizes_status_transport_and_json(monkeypatch) -> None:
    descriptor = _dashboard_descriptor()
    request_limit = dashboard_runtime._MAX_CONTROL_REQUEST_BYTES
    monkeypatch.setattr(dashboard_runtime, "_MAX_CONTROL_REQUEST_BYTES", 4)
    with pytest.raises(ValueError, match="request exceeds"):
        dashboard_runtime.dashboard_api_request(
            "/api/runtime/toggle",
            method="POST",
            payload={"enabled": True},
            descriptor=descriptor,
        )

    monkeypatch.setattr(dashboard_runtime, "_MAX_CONTROL_REQUEST_BYTES", request_limit)
    monkeypatch.setattr(dashboard_runtime, "_MAX_CONTROL_RESPONSE_BYTES", 4)
    monkeypatch.setattr(
        dashboard_runtime,
        "open_no_redirect",
        lambda *_args, **_kw: _DashboardResponse(b"12345"),
    )
    with pytest.raises(ValueError, match="response exceeds"):
        dashboard_runtime.dashboard_api_request("/api/runtime", descriptor=descriptor)

    monkeypatch.setattr(dashboard_runtime, "_MAX_CONTROL_RESPONSE_BYTES", 1024)
    monkeypatch.setattr(
        dashboard_runtime,
        "open_no_redirect",
        lambda *_args, **_kw: _DashboardResponse(b"{}", status=500),
    )
    with pytest.raises(ValueError, match="rejected"):
        dashboard_runtime.dashboard_api_request("/api/runtime", descriptor=descriptor)

    monkeypatch.setattr(
        dashboard_runtime,
        "open_no_redirect",
        lambda *_args, **_kw: _raise(dashboard_runtime.urllib.error.URLError("offline")),
    )
    with pytest.raises(ValueError, match="not reachable"):
        dashboard_runtime.dashboard_api_request("/api/runtime", descriptor=descriptor)

    response_body = io.BytesIO(b"denied")
    http_error = dashboard_runtime.urllib.error.HTTPError(
        "url",
        403,
        "denied",
        None,
        response_body,
    )
    monkeypatch.setattr(
        dashboard_runtime,
        "open_no_redirect",
        lambda *_args, **_kw: _raise(http_error),
    )
    with pytest.raises(ValueError, match="HTTP 403"):
        dashboard_runtime.dashboard_api_request("/api/runtime", descriptor=descriptor)
    assert response_body.closed is True

    monkeypatch.setattr(
        dashboard_runtime,
        "open_no_redirect",
        lambda *_args, **_kw: _DashboardResponse(b"not json"),
    )
    with pytest.raises(ValueError, match="response is invalid"):
        dashboard_runtime.dashboard_api_request("/api/runtime", descriptor=descriptor)

    monkeypatch.setattr(
        dashboard_runtime,
        "open_no_redirect",
        lambda *_args, **_kw: _DashboardResponse(b"[]"),
    )
    with pytest.raises(ValueError, match="must be a JSON object"):
        dashboard_runtime.dashboard_api_request("/api/runtime", descriptor=descriptor)

    monkeypatch.setattr(
        dashboard_runtime,
        "open_no_redirect",
        lambda *_args, **_kw: _DashboardResponse(b'{"enabled":true}'),
    )
    assert dashboard_runtime.dashboard_api_request("/api/runtime", descriptor=descriptor) == {
        "enabled": True
    }
    assert dashboard_runtime.dashboard_api_request(
        "/api/runtime/toggle",
        method="POST",
        payload={"enabled": True},
        descriptor=descriptor,
    ) == {"enabled": True}
