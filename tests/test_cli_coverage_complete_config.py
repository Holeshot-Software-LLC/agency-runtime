"""Behavior coverage for configuration CLI branches."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

from agency_runtime.cli import config_commands as subject


def args(**changes):
    values = {
        "clear": False,
        "force": False,
        "json": False,
        "key": "profile",
        "non_interactive": True,
        "profile": "standard",
        "prompt": False,
        "raw": False,
        "stdin": False,
        "value": None,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def detection(available=True):
    return SimpleNamespace(
        providers=SimpleNamespace(
            ollama_available=available,
            ollama_base_url="http://127.0.0.1:11434",
            ollama_models=["model"] if available else [],
            openai_key="key" if available else "",
            anthropic_key="",
            litellm_available=False,
            litellm_base_url="http://127.0.0.1:4000",
        ),
        adapters=SimpleNamespace(
            hermes=available,
            openclaw=False,
            codex=available,
            claude=False,
        ),
    )


def deps(**changes):
    config = SimpleNamespace(
        config_path=None,
        store=SimpleNamespace(resolved_path=lambda: "agency.db"),
    )
    values = {
        "load_config": lambda **_kwargs: config,
        "store_factory": lambda _config: object(),
        "seed_starter_roster": lambda _store: 2,
        "detect_for_profile": lambda _profile: detection(),
        "interactive_wizard": lambda _detection, profile: {
            "profile": profile,
            "providers": [],
        },
        "validate_chain": lambda _providers: True,
        "secret_prompt": lambda _prompt: "secret",
        "configure_console": lambda: None,
    }
    values.update(changes)
    return subject.ConfigurationDependencies(**values)


def test_stdin_reader_supports_document_line_and_bound(monkeypatch):
    monkeypatch.setattr(subject.sys, "stdin", io.StringIO("value\nremaining"))
    assert subject._read_stdin_bounded(limit=20) == "value\nremaining"
    monkeypatch.setattr(subject.sys, "stdin", io.StringIO("secret\r\nremaining"))
    assert subject._read_stdin_bounded(limit=20, line=True) == "secret"
    monkeypatch.setattr(subject.sys, "stdin", io.StringIO("12345\n"))
    with pytest.raises(ValueError, match="size limit"):
        subject._read_stdin_bounded(limit=4, line=True)


def test_configure_existing_file_abort_and_noninteractive_refusal(tmp_path, monkeypatch, capsys):
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    monkeypatch.setattr(subject, "resolve_config_path", lambda: path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    assert subject.cmd_configure(args(non_interactive=False), dependencies=deps()) == 0
    assert "Aborted" in capsys.readouterr().out
    assert subject.cmd_configure(args(), dependencies=deps()) == 1
    assert "Use --force" in capsys.readouterr().out


def test_configure_validation_failure_never_writes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(subject, "resolve_config_path", lambda: tmp_path / "agency.yaml")
    monkeypatch.setattr(
        subject,
        "replace_config_document",
        lambda *_a, **_kw: pytest.fail("must not write"),
    )
    assert (
        subject.cmd_configure(
            args(non_interactive=False),
            dependencies=deps(validate_chain=lambda _providers: False),
        )
        == 1
    )
    assert "validation failed" in capsys.readouterr().out


def test_configure_interactive_overwrite_uses_revision_and_seeds(tmp_path, monkeypatch, capsys):
    path = tmp_path / "agency.yaml"
    path.write_text("invalid: [\n", encoding="utf-8")
    writes = []
    profiles = []
    monkeypatch.setattr(subject, "resolve_config_path", lambda: path)
    monkeypatch.setattr(subject, "read_config_revision", lambda _path: "revision")
    monkeypatch.setattr(
        subject,
        "replace_config_document",
        lambda document, **kwargs: writes.append((document, kwargs)),
    )
    monkeypatch.setattr(subject, "reset_config_cache", lambda: None)
    monkeypatch.setattr(subject, "_prompt_install_profile", lambda: "power")
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    dependencies = deps(
        detect_for_profile=lambda profile: profiles.append(profile) or detection(False)
    )
    assert (
        subject.cmd_configure(args(non_interactive=False, profile=None), dependencies=dependencies)
        == 0
    )
    assert profiles == ["power"]
    assert writes[0][1] == {
        "expected_revision": "revision",
        "path": path,
        "recover_invalid_existing": True,
    }
    assert "SQLite database initialized: agency.db" in capsys.readouterr().out


def test_configure_noninteractive_generates_new_document(tmp_path, monkeypatch):
    path = tmp_path / "agency.yaml"
    writes = []
    monkeypatch.setattr(subject, "resolve_config_path", lambda: path)
    monkeypatch.setattr(
        subject, "read_config_state", lambda _path: SimpleNamespace(revision="empty")
    )
    monkeypatch.setattr(
        subject,
        "generate_config_from_detection",
        lambda _detection, profile: {"profile": profile, "providers": []},
    )
    monkeypatch.setattr(
        subject,
        "replace_config_document",
        lambda document, **kwargs: writes.append((document, kwargs)),
    )
    monkeypatch.setattr(subject, "reset_config_cache", lambda: None)
    assert subject.cmd_configure(args(profile="local-only"), dependencies=deps()) == 0
    assert writes[0][0]["profile"] == "local-only"
    assert writes[0][1]["expected_revision"] == "empty"
    assert writes[0][1]["recover_invalid_existing"] is False


@pytest.mark.parametrize("json_mode", [False, True])
def test_doctor_show_and_path_render_modes(tmp_path, monkeypatch, capsys, json_mode):
    report = SimpleNamespace(exit_code=2, to_dict=lambda: {"exit_code": 2})
    emitted = []
    monkeypatch.setattr(subject, "run_doctor", lambda _config: report)
    monkeypatch.setattr(subject, "format_report_human", lambda _report: "human")
    monkeypatch.setattr(subject, "_print_json", emitted.append)
    assert subject.cmd_doctor(args(json=json_mode), dependencies=deps()) == 2
    assert bool(emitted) is json_mode
    if not json_mode:
        assert "human" in capsys.readouterr().out
    monkeypatch.setattr(
        subject,
        "config_to_yaml",
        lambda _config, *, redact: f"redact={redact}",
    )
    assert subject.cmd_config_show(args(raw=json_mode), dependencies=deps()) == 0
    assert f"redact={not json_mode}" in capsys.readouterr().out

    path = tmp_path / "missing.yaml"
    monkeypatch.setattr(subject, "resolve_config_path", lambda: path)
    assert subject.cmd_config_path(args()) == 0
    assert "bundled defaults" in capsys.readouterr().out
    path.write_text("profile: standard\n", encoding="utf-8")
    assert subject.cmd_config_path(args()) == 0
    assert "bundled defaults" not in capsys.readouterr().out


class Lookup:
    attribute = "attribute-value"

    def __init__(self):
        self.providers = [{"name": "first"}]

    def __getitem__(self, key):
        if key == "mapping":
            return "mapping-value"
        if key == "type-error":
            raise TypeError("bad lookup")
        raise KeyError(key)


@pytest.mark.parametrize(
    ("key", "code", "text"),
    [
        ("attribute", 0, "attribute-value"),
        ("providers.0.name", 0, "first"),
        ("mapping", 0, "mapping-value"),
        ("providers.missing", 1, "Key not found"),
        ("unknown", 1, "Key not found"),
        ("type-error", 1, "Key not found"),
        ("attribute.extra", 1, "Key not found"),
    ],
)
def test_config_get_supported_shapes_and_missing(capsys, key, code, text):
    dependencies = deps(load_config=lambda: Lookup())
    assert subject.cmd_config_get(args(key=key), dependencies=dependencies) == code
    captured = capsys.readouterr()
    assert text in captured.out + captured.err


def test_config_set_operation_validation_and_channels(monkeypatch):
    dependencies = deps(secret_prompt=lambda _prompt: "prompted")
    cases = [
        (args(clear=True, prompt=True), False, "mutually exclusive"),
        (args(clear=True), False, "valid only for a secret"),
        (args(clear=True, value="x", key="api_key"), True, "valid only"),
        (args(value="visible", key="api_key"), True, "not accepted"),
        (args(key="api_key"), True, "secret updates require"),
        (args(prompt=True), False, "valid only for secret"),
        (args(stdin=True, value="x"), False, "either a positional"),
        (args(), False, "requires a value"),
        (args(value="["), False, "not valid YAML"),
    ]
    for value, secret, message in cases:
        with pytest.raises(ValueError, match=message):
            subject._config_set_operation(value, is_secret=secret, dependencies=dependencies)
    assert (
        subject._config_set_operation(
            args(clear=True, key="api_key"),
            is_secret=True,
            dependencies=dependencies,
        )["action"]
        == "clear"
    )
    assert (
        subject._config_set_operation(
            args(prompt=True, key="api_key"),
            is_secret=True,
            dependencies=dependencies,
        )["value"]
        == "prompted"
    )
    monkeypatch.setattr(subject.sys, "stdin", io.StringIO("stdin-secret\n"))
    assert (
        subject._config_set_operation(
            args(stdin=True, key="api_key"),
            is_secret=True,
            dependencies=dependencies,
        )["value"]
        == "stdin-secret"
    )
    monkeypatch.setattr(subject.sys, "stdin", io.StringIO("power"))
    assert (
        subject._config_set_operation(args(stdin=True), is_secret=False, dependencies=dependencies)[
            "value"
        ]
        == "power"
    )
    assert (
        subject._plain_config_set_operation(args(key="adapters.codex.enabled", value="true"))[
            "value"
        ]
        == "true"
    )
    assert (
        subject._plain_config_set_operation(args(key="adapters.codex.enabled", value="false"))[
            "value"
        ]
        == "false"
    )
    assert subject._normalize_config_set_value("profile", True) is True


def test_config_set_applies_revision_and_reports_effects(monkeypatch, capsys):
    operations = []
    monkeypatch.setattr(subject, "read_config_state", lambda: SimpleNamespace(revision="revision"))
    result = SimpleNamespace(
        policy_enforced=True,
        restart_required=["judge.model"],
        state=SimpleNamespace(
            effective={"judge": {"model": "effective"}},
            environment_overrides={"judge.model": "AGENCY_JUDGE_MODEL"},
        ),
    )
    monkeypatch.setattr(
        subject,
        "apply_config_operations",
        lambda value, **kwargs: operations.append((value, kwargs)) or result,
    )
    assert (
        subject.cmd_config_set(args(key="judge.model", value="configured"), dependencies=deps())
        == 0
    )
    assert operations[0][1] == {"expected_revision": "revision"}
    output = capsys.readouterr().out
    assert "overridden by AGENCY_JUDGE_MODEL" in output
    assert "local-only policy enforced" in output
    assert "restart required: judge.model" in output
    with pytest.raises(ValueError, match="non-empty dotted path"):
        subject.cmd_config_set(args(key="judge..model", value="x"), dependencies=deps())


@pytest.mark.parametrize(
    ("exit_code", "expected"),
    [(0, "all checks passed"), (2, "degraded"), (1, "has issues")],
)
def test_config_validate_health_and_checks(monkeypatch, capsys, exit_code, expected):
    checks = [
        SimpleNamespace(status="pass", name="pass", message="ok"),
        SimpleNamespace(status="warn", name="warn", message="warning"),
        SimpleNamespace(status="fail", name="fail", message="failure"),
    ]
    monkeypatch.setattr(
        subject,
        "run_doctor",
        lambda _config: SimpleNamespace(exit_code=exit_code, checks=checks),
    )
    assert subject.cmd_config_validate(args(), dependencies=deps()) == exit_code
    output = capsys.readouterr().out
    assert expected in output
    assert "warn: warning" in output and "fail: failure" in output
    assert "pass: ok" not in output


def test_config_reset_missing_abort_and_confirm(tmp_path, monkeypatch, capsys):
    path = tmp_path / "agency.yaml"
    dependencies = deps(load_config=lambda: SimpleNamespace(config_path=str(path)))
    assert subject.cmd_config_reset(args(), dependencies=dependencies) == 0
    assert "Config reset" in capsys.readouterr().out
    path.write_text("profile: standard\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    assert subject.cmd_config_reset(args(), dependencies=dependencies) == 0
    assert path.exists() and "Aborted" in capsys.readouterr().out
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    assert subject.cmd_config_reset(args(), dependencies=dependencies) == 0
    assert not path.exists()
