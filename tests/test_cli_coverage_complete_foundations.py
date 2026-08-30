"""Behavior coverage for CLI facade, service, and shared boundary helpers."""

from __future__ import annotations

import runpy
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime import __version__
from agency_runtime.cli import _common
from agency_runtime.cli import entrypoint as cli_entrypoint
from agency_runtime.cli import main as cli
from agency_runtime.cli import service_commands as services
from tests.runtime_support import trusted_test_interpreter


def _args(**overrides):
    defaults = {
        "agent": None,
        "all": False,
        "backend": "codex",
        "command": None,
        "config": None,
        "dashboard_service_action": "status",
        "db": None,
        "dry_run": False,
        "json": False,
        "no_open": False,
        "service_mode": False,
        "task": "review this change",
        "timeout": None,
        "workdir": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_common_store_json_console_and_secret_helpers(monkeypatch, capsys):
    opened = []

    class FakeStore:
        def __init__(self, path=None):
            opened.append(path)

    monkeypatch.setattr(_common, "Store", FakeStore)
    config = SimpleNamespace(store=SimpleNamespace(resolved_path=lambda: "configured.db"))
    assert isinstance(_common.store(config), FakeStore)
    assert isinstance(_common.store(), FakeStore)
    assert opened == ["configured.db", None]

    _common.print_json({"z": 1, "a": 2})
    assert capsys.readouterr().out == '{\n  "a": 2,\n  "z": 1\n}\n'

    calls = []

    class GoodStream:
        def reconfigure(self, **kwargs):
            calls.append(kwargs)

    class RejectingStream:
        def reconfigure(self, **_kwargs):
            raise OSError("detached")

    monkeypatch.setattr(_common.sys, "stdout", GoodStream())
    monkeypatch.setattr(_common.sys, "stderr", RejectingStream())
    _common.configure_console_output()
    assert calls == [{"errors": "backslashreplace"}]

    monkeypatch.setattr(_common.sys, "stdout", object())
    monkeypatch.setattr(_common.sys, "stderr", object())
    _common.configure_console_output()

    assert _common.is_secret_config_part("client-secret")
    assert _common.is_secret_config_part("service_token")
    assert not _common.is_secret_config_part("api_key_env")
    assert not _common.is_secret_config_part("model")


def test_common_config_projection_formatting_and_nested_paths():
    @dataclass
    class Nested:
        token: str
        values: tuple[int, ...]

    value = {
        "nested": Nested("secret", (1, 2)),
        "items": [{"password": "hidden"}, "plain"],
        "empty_secret": "",
    }
    projected = _common.config_display_value(value)
    assert projected["nested"]["token"] == _common.REDACTED
    assert projected["nested"]["values"] == [1, 2]
    assert projected["items"][0]["password"] == _common.REDACTED
    assert projected["empty_secret"] == ""
    assert _common.config_display_value(value, raw=True)["nested"]["token"] == "secret"
    assert _common.format_config_value(Nested("x", (1,))) == '{"token": "x", "values": [1]}'
    assert _common.format_config_value("plain") == "plain"

    document = {"providers": [{"name": "first"}]}
    assert _common.nested_config_value(document, ["providers", "0", "name"]) == "first"
    with pytest.raises(ValueError, match="invalid literal"):
        _common.nested_config_value(document, ["providers", "missing"])
    with pytest.raises(KeyError, match=r"providers\.0\.name\.missing"):
        _common.nested_config_value(document, ["providers", "0", "name", "missing"])


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://localhost:1", True),
        ("http://127.0.0.1:1", True),
        ("http://[::1]:1", True),
        ("https://example.invalid", False),
        ("not a url", False),
        ("http://[malformed", False),
    ],
)
def test_common_loopback_classification(value, expected):
    assert _common.is_loopback_url(value) is expected


def test_common_local_only_enforcement_handles_malformed_and_mixed_input():
    untouched = {"profile": "standard"}
    assert _common.enforce_local_only_config(untouched) is untouched

    data = {
        "profile": " LOCAL-ONLY ",
        "ollama": "invalid",
        "judge": "invalid",
        "providers": [
            "invalid",
            {"name": "remote", "type": "anthropic", "base_url": "https://remote.invalid"},
            {
                "name": "local",
                "type": "openai-compatible",
                "base_url": "http://127.0.0.1:9000/v1",
                "model": "local-model",
                "api_key": "remove",
                "api_key_env": "REMOVE",
                "transport": "remote",
            },
        ],
        "adapters": "invalid",
    }
    result = _common.enforce_local_only_config(data)
    assert result["ollama"]["base_url"] == "http://127.0.0.1:11434"
    assert result["providers"] == [
        {
            "name": "local",
            "type": "openai-compatible",
            "base_url": "http://127.0.0.1:9000/v1",
            "model": "local-model",
            "api_key": "",
            "api_key_env": "",
            "transport": "",
            "ollama_mode": False,
        }
    ]
    assert result["judge"]["model"] == "local-model"
    assert all(entry == {"enabled": "false"} for entry in result["adapters"].values())

    fallback = _common.enforce_local_only_config(
        {
            "profile": "local-only",
            "ollama": {"base_url": "https://remote.invalid", "model": "local"},
            "providers": "invalid",
            "judge": {"timeout": 7},
            "adapters": {"codex": "invalid"},
        }
    )
    assert fallback["providers"][0]["type"] == "ollama"
    assert fallback["providers"][0]["timeout"] == 7.0
    assert fallback["adapters"]["codex"] == {"enabled": "false"}


def test_service_entrypoints_forward_process_boundaries(monkeypatch):
    import agency_runtime.adapters.hooks as hooks
    import agency_runtime.server.dashboard as dashboard
    import agency_runtime.server.http as http
    import agency_runtime.server.mcp as mcp

    calls = []
    monkeypatch.setattr(http, "serve", lambda: calls.append(("serve",)))
    monkeypatch.setattr(mcp, "run_stdio", lambda **kwargs: calls.append(("mcp", kwargs)) or 7)
    monkeypatch.setattr(
        hooks,
        "run_hook_stdio",
        lambda host, **kwargs: calls.append(("hook", host, kwargs)) or 8,
    )
    monkeypatch.setattr(
        dashboard,
        "run_dashboard",
        lambda **kwargs: calls.append(("dashboard", kwargs)),
    )
    assert services.cmd_serve(_args()) == 0
    assert services.cmd_mcp(_args(db="one.db")) == 7
    assert services.cmd_mcp(_args(db=None)) == 7
    assert services.cmd_mcp(_args(db=None, config="operator.yaml")) == 7
    assert services.cmd_hook(_args(db="two.db", host="codex")) == 8
    assert services.cmd_hook(_args(db=None, host="claude")) == 8
    assert (
        services.cmd_dashboard(
            _args(port=9000, db="three.db", no_open=True, service_mode=True, config="cfg")
        )
        == 0
    )
    assert calls == [
        ("serve",),
        ("mcp", {"db_path": "one.db", "config_path": None}),
        ("mcp", {"db_path": None, "config_path": None}),
        ("mcp", {"db_path": None, "config_path": "operator.yaml"}),
        (
            "hook",
            "codex",
            {
                "db_path": "two.db",
                "config_path": None,
                "runtime_control_path": None,
                "expected_event": "",
            },
        ),
        (
            "hook",
            "claude",
            {
                "db_path": None,
                "config_path": None,
                "runtime_control_path": None,
                "expected_event": "",
            },
        ),
        (
            "dashboard",
            {
                "port": 9000,
                "db_path": "three.db",
                "open_browser": False,
                "service_mode": True,
                "config_path": "cfg",
            },
        ),
    ]


def test_dashboard_readiness_success_and_timeout(monkeypatch):
    import agency_runtime.core.dashboard_runtime as runtime

    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kwargs: True)
    moments = iter([0.0, 0.1])
    monkeypatch.setattr(services.time, "monotonic", lambda: next(moments))
    monkeypatch.setattr(services.time, "sleep", lambda _delay: None)
    assert services._wait_dashboard_ready(1.0) is True

    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kwargs: False)
    moments = iter([0.0, 0.1, 2.0])
    monkeypatch.setattr(services.time, "monotonic", lambda: next(moments))
    assert services._wait_dashboard_ready(1.0) is False


@pytest.mark.parametrize(
    ("action", "dry_run", "expected"),
    [
        ("open", False, "open"),
        ("status", False, "status"),
        ("install", True, "plan"),
        ("install", False, "install"),
        ("start", False, "start"),
        ("stop", False, "stop"),
        ("restart", False, "restart"),
        ("uninstall", False, "uninstall"),
    ],
)
def test_dashboard_service_dispatches_every_action(monkeypatch, action, dry_run, expected):
    import agency_runtime.core.dashboard_runtime as runtime
    import agency_runtime.core.dashboard_service as dashboard_service

    emitted = []
    calls = []

    def operation(name):
        return lambda *args, **kwargs: (
            calls.append((name, args, kwargs))
            or {
                "ok": True,
                "exit_code": 7,
                "action": name,
            }
        )

    monkeypatch.setattr(runtime, "open_dashboard_service", operation("open"))
    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kwargs: True)
    for name in ("inspect", "install", "plan", "restart", "start", "stop", "uninstall"):
        monkeypatch.setattr(
            dashboard_service,
            f"{name}_dashboard_service",
            operation("status" if name == "inspect" else name),
        )
    monkeypatch.setattr(services, "resolve_config_path", lambda: "agency.yaml")
    monkeypatch.setattr(services, "_print_json", emitted.append)

    assert (
        services.cmd_dashboard_service(
            _args(dashboard_service_action=action, dry_run=dry_run, json=True)
        )
        == 7
    )
    assert calls[0][0] == expected
    assert emitted[0]["action"] == expected


@pytest.mark.parametrize(
    ("action", "result", "expected"),
    [
        ("open", {"ok": True, "url": "http://127.0.0.1:7914"}, "127.0.0.1"),
        (
            "install",
            {"ok": True, "status": "registered", "reachable": False},
            "not reachable",
        ),
        ("status", {"ok": False, "error": "missing"}, "missing"),
    ],
)
def test_dashboard_service_human_rendering(monkeypatch, capsys, action, result, expected):
    import agency_runtime.core.dashboard_runtime as runtime
    import agency_runtime.core.dashboard_service as dashboard_service

    monkeypatch.setattr(services, "resolve_config_path", lambda: "agency.yaml")
    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kwargs: True)
    monkeypatch.setattr(runtime, "open_dashboard_service", lambda **_kwargs: result)
    monkeypatch.setattr(dashboard_service, "install_dashboard_service", lambda **_kwargs: result)
    monkeypatch.setattr(dashboard_service, "inspect_dashboard_service", lambda **_kwargs: result)
    assert services.cmd_dashboard_service(_args(dashboard_service_action=action, json=False)) == (
        0 if result["ok"] else 1
    )
    assert expected in capsys.readouterr().out


def test_dashboard_service_rejects_unknown_action():
    with pytest.raises(ValueError, match="unknown dashboard service action"):
        services.cmd_dashboard_service(_args(dashboard_service_action="invalid"))


def test_facade_thin_wrappers_forward_to_cohesive_modules(monkeypatch):
    sentinel = object()
    detection = SimpleNamespace(providers=SimpleNamespace())
    monkeypatch.setattr(cli._wizard, "_new_provider_entry", lambda *a, **kw: (a, kw))
    monkeypatch.setattr(cli._wizard, "_pick_openai_model", lambda *a, **kw: (a, kw))
    monkeypatch.setattr(cli._wizard, "_pick_anthropic_model", lambda **kw: kw)
    monkeypatch.setattr(cli._wizard, "_pick_litellm_model", lambda *a, **kw: (a, kw))
    monkeypatch.setattr(cli._wizard, "_prompt_provider_auth", lambda **kw: (kw, "key"))
    assert cli._new_provider_entry(detection, "standard")[0] == (detection, "standard")
    assert cli._pick_openai_model(detection.providers)[0] == (detection.providers,)
    assert "dependencies" in cli._pick_anthropic_model()
    assert cli._pick_litellm_model(detection.providers)[0] == (detection.providers,)
    assert cli._prompt_provider_auth(default_env="KEY", base_url="http://localhost")[1] == "key"

    monkeypatch.setattr(cli._install, "_cmd_host_control", lambda *a, **kw: (a, kw))
    monkeypatch.setattr(cli._install, "cmd_host_canary", lambda *a, **kw: sentinel)
    args = _args()
    assert cli._cmd_host_control(args, enabled=True)[1]["enabled"] is True
    assert cli.cmd_host_canary(args) is sentinel

    for name in (
        "cmd_doctor",
        "cmd_config_show",
        "cmd_config_path",
        "cmd_config_validate",
        "cmd_config_reset",
    ):
        monkeypatch.setattr(cli._config, name, lambda *a, _name=name, **kw: (_name, a, kw))
    assert cli.cmd_doctor(args)[0] == "cmd_doctor"
    assert cli.cmd_config_show(args)[0] == "cmd_config_show"
    assert cli.cmd_config_path(args)[0] == "cmd_config_path"
    assert cli.cmd_config_validate(args)[0] == "cmd_config_validate"
    assert cli.cmd_config_reset(args)[0] == "cmd_config_reset"


def test_python_module_entrypoint_exits_with_main_status(monkeypatch):
    monkeypatch.setattr(cli_entrypoint, "main", lambda: 23)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("agency_runtime.cli.__main__", run_name="__main__")
    assert exc.value.code == 23


def test_python_module_version_probe_keeps_the_full_cli_graph_unloaded() -> None:
    source_root = Path(__file__).resolve().parents[1]
    script = f"""
import runpy
import sys
sys.path.insert(0, {str(source_root)!r})
sys.argv = ["agency", "--version"]
try:
    runpy.run_module("agency_runtime.cli.__main__", run_name="__main__")
except SystemExit as exc:
    assert exc.code == 0
else:
    raise AssertionError("module entry point did not exit")
assert "agency_runtime.cli.main" not in sys.modules
assert "agency_runtime.cli.eval_commands" not in sys.modules
assert "agency_runtime.core.evals.upstream_selection" not in sys.modules
assert "yaml" not in sys.modules
"""
    completed = subprocess.run(
        [str(trusted_test_interpreter()), "-I", "-S", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == f"agency {__version__}\n"
