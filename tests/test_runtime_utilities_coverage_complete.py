"""Complete the behavioral matrix for small cross-platform runtime utilities."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request

import pytest

from agency_runtime.core import process_argv as process_argv_module
from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.display import has_terminal_control, safe_display_token
from agency_runtime.core.host_control import (
    SUPPORTED_HOSTS,
    inspect_all_host_statuses,
    inspect_host_status,
    normalize_host,
    set_runtime_control,
)
from agency_runtime.core.http_safety import _is_loopback_destination, open_no_redirect
from agency_runtime.core.policy.profiles import DEFAULT_PROFILE, get_profile
from agency_runtime.core.process_argv import (
    absolute_executable_path,
    agency_bootstrap_path,
    isolated_python_argv,
    prepare_process_argv,
)
from agency_runtime.core.provider_validation import validate_provider
from agency_runtime.core.receipts.host import extract_host_receipt
from agency_runtime.core.receipts.litellm import extract_litellm_receipt_headers
from agency_runtime.core.selector import stickiness
from agency_runtime.core.selector.explain import _agent_summary, _clamp_limit, _domain_terms
from agency_runtime.core.selector.intent_text import mask_excluded_intent
from agency_runtime.core.store.sqlite import Store


class _Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_absolute_executable_path_preserves_virtualenv_launcher(tmp_path: Path) -> None:
    interpreter = tmp_path / "python3.12"
    interpreter.write_bytes(b"python")
    virtualenv_python = tmp_path / ".venv" / "bin" / "python"
    virtualenv_python.parent.mkdir(parents=True)
    try:
        virtualenv_python.symlink_to(interpreter)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable on this host: {exc}")

    assert absolute_executable_path(virtualenv_python) == str(virtualenv_python.absolute())
    assert absolute_executable_path(virtualenv_python) != str(interpreter.resolve())


@pytest.mark.parametrize(
    "value",
    [
        r"C:\Program Files\O'Brien & Sons\python.exe",
        r"\\build-host\agency-runtime\venv\Scripts\python.exe",
    ],
)
def test_absolute_executable_path_preserves_foreign_windows_absolute_paths(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_native_abspath(_value: str) -> str:
        raise AssertionError("foreign Windows path reached native abspath")

    monkeypatch.setattr(process_argv_module.os.path, "abspath", unexpected_native_abspath)

    assert absolute_executable_path(value) == value


def test_absolute_executable_path_absolutizes_relative_native_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert absolute_executable_path(Path("venv") / "python") == str(
        (tmp_path / "venv" / "python").absolute()
    )


@pytest.mark.parametrize("value", ["", "bad\x00path"])
def test_absolute_executable_path_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="invalid character"):
        absolute_executable_path(value)


def test_isolated_bootstrap_ignores_hostile_cwd_and_supports_user_site_layout(
    tmp_path: Path,
) -> None:
    import agency_runtime

    user_site = tmp_path / "user-site"
    installed_package = user_site / "agency_runtime"
    shutil.copytree(
        Path(agency_runtime.__file__).parent,
        installed_package,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    hostile = tmp_path / "hostile"
    hostile_package = hostile / "agency_runtime"
    hostile_package.mkdir(parents=True)
    marker = tmp_path / "shadow-loaded"
    hostile_package.joinpath("__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('loaded')\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(hostile)
    environment["PYTHONHOME"] = str(tmp_path / "hostile-python-home")
    bootstrap = installed_package / "_bootstrap.py"

    completed = subprocess.run(
        [sys.executable, "-I", str(bootstrap), "agency_runtime.cli", "--help"],
        cwd=hostile,
        env=environment,
        capture_output=True,
        timeout=30,
        check=False,
    )

    stdout = completed.stdout.decode("utf-8", errors="strict")
    stderr = completed.stderr.decode("utf-8", errors="strict")
    assert completed.returncode == 0, stderr
    assert "Agency Runtime" in stdout
    assert not marker.exists()


def test_isolated_python_argv_binds_absolute_interpreter_and_package_bootstrap() -> None:
    argv = isolated_python_argv("relative/python", "agency_runtime.cli", "--help")

    assert Path(argv[0]).is_absolute()
    assert argv[1:] == [
        "-I",
        agency_bootstrap_path(),
        "agency_runtime.cli",
        "--help",
    ]


def test_display_tokens_validate_escape_and_truncate() -> None:
    with pytest.raises(ValueError, match="positive"):
        safe_display_token("value", limit=0)
    assert safe_display_token("abcdef", limit=5) == "ab..."
    assert safe_display_token("abcdef", limit=2) == ".."
    assert safe_display_token("ok") == "ok"
    assert safe_display_token("a\x1bb") == "a\\u001bb"
    assert has_terminal_control("safe") is False
    assert has_terminal_control("unsafe\x7f") is True


def test_http_loopback_recognizes_localhost_and_uses_proxy_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _is_loopback_destination("http://localhost./v1") is True
    assert _is_loopback_destination("http://example.invalid/v1") is False
    captured: dict[str, Any] = {}

    class _Opener:
        def open(self, request: Request, *, timeout: float) -> str:
            captured.update(url=request.full_url, timeout=timeout)
            return "response"

    def build_opener(*handlers: object) -> _Opener:
        captured["handlers"] = handlers
        return _Opener()

    monkeypatch.setattr("agency_runtime.core.http_safety.urllib.request.build_opener", build_opener)
    assert open_no_redirect(Request("http://localhost/status"), timeout=1) == "response"
    assert captured["url"] == "http://localhost/status"
    assert len(captured["handlers"]) == 2


def test_process_argv_rejects_invalid_inputs_and_preserves_posix_resolution() -> None:
    for value in ([], "agent"):
        with pytest.raises(TypeError, match="non-empty"):
            prepare_process_argv(value, resolver=lambda _name: "agent")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="non-empty"):
        prepare_process_argv(["agent", 2], resolver=lambda _name: "agent")  # type: ignore[list-item]
    for value in ([""], ["agent", "bad\x00arg"]):
        with pytest.raises(ValueError, match="invalid"):
            prepare_process_argv(value, resolver=lambda _name: "agent")
    with pytest.raises(FileNotFoundError, match="executable not found"):
        prepare_process_argv(["missing"], resolver=lambda _name: None)
    assert prepare_process_argv(
        ["agent", "task"], platform_name="posix", resolver=lambda _name: "/usr/bin/agent"
    ) == ["/usr/bin/agent", "task"]


def test_process_argv_wraps_a_powershell_script_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.name != "nt":
        monkeypatch.setattr(
            process_argv_module,
            "_is_absolute_path",
            lambda value, *, platform_name: Path(value).is_absolute(),
        )
        monkeypatch.setattr(
            process_argv_module,
            "ntpath",
            process_argv_module.posixpath,
        )
    script = tmp_path / "agent.ps1"
    powershell = tmp_path / "powershell.exe"
    script.write_text("exit 0", encoding="utf-8")
    powershell.write_bytes(b"powershell")
    result = prepare_process_argv(
        ["agent", "task"],
        platform_name="nt",
        resolver=lambda _name: str(script),
        system_resolver=lambda _name: str(powershell),
    )
    assert result[:7] == [
        str(powershell),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
    ]
    assert result[-2:] == [str(script), "task"]


def test_provider_validation_covers_cli_and_required_configuration() -> None:
    cli = ProviderEntry(name="codex", type="cli", transport="codex")
    result = validate_provider(
        cli,
        cli_inspector=lambda *_args, **_kwargs: type(
            "Status",
            (),
            {"usable": True, "reason": "", "installed": True, "authenticated": True},
        )(),
    )
    assert result.usable is result.installed is result.authenticated is True

    for provider in (
        ProviderEntry(name="missing-model", base_url="https://example.invalid/v1", api_key="x"),
        ProviderEntry(name="missing-url", model="model", api_key="x"),
    ):
        result = validate_provider(provider)
        assert result.reason == "model and base URL are required"

    keyless = ProviderEntry(
        name="keyless",
        type="anthropic",
        model="model",
        base_url="https://example.invalid/v1",
    )
    assert validate_provider(keyless).reason == "configured authentication is unavailable"


def test_provider_validation_anthropic_headers_and_keyless_loopback() -> None:
    seen: list[dict[str, str]] = []

    def respond(request: Request, **_kwargs: Any) -> _Response:
        seen.append({name.casefold(): value for name, value in request.header_items()})
        return _Response(200)

    anthropic = ProviderEntry(
        name="anthropic",
        type="anthropic",
        model="claude",
        base_url="https://api.example.invalid/v1",
        api_key="secret",
    )
    assert validate_provider(anthropic, opener=respond).authenticated is True
    assert seen[0]["x-api-key"] == "secret"
    assert seen[0]["anthropic-version"] == "2023-06-01"

    loopback = ProviderEntry(
        name="local",
        type="openai-compatible",
        model="local",
        base_url="http://127.0.0.1:4000/v1",
    )
    result = validate_provider(loopback, opener=respond)
    assert result.usable is True
    assert result.authenticated is None


def test_install_profiles_default_normalize_and_reject_unknown() -> None:
    assert get_profile() is DEFAULT_PROFILE
    assert get_profile(" POWER ").name == "power"
    with pytest.raises(ValueError, match="unknown profile"):
        get_profile("missing")


def test_receipt_helpers_cover_non_mapping_null_and_invalid_fields() -> None:
    assert extract_host_receipt(None)["source"] == "unknown"
    assert extract_litellm_receipt_headers(object())["model_group"] == ""
    headers = {
        None: "ignored",
        "x-litellm-model-group": None,
        "x-litellm-attempted-fallbacks": "invalid",
    }
    assert extract_litellm_receipt_headers(headers)["attempted_fallbacks"] == 0


def test_host_control_validates_postconditions_and_default_inspectors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="unsupported host"):
        normalize_host("other")

    class _MismatchedStore:
        def set_host_control(self, *_args: object, **_kwargs: object) -> dict[str, bool]:
            return {"enabled": False}

        def get_host_control(self, *_args: object) -> dict[str, bool]:
            return {"enabled": False}

    with pytest.raises(RuntimeError, match="postcondition"):
        set_runtime_control(_MismatchedStore(), "codex", enabled=True, source="test")  # type: ignore[arg-type]

    store = Store(tmp_path / "agency.db")
    inventory = [
        {"host": "codex", "registered": False, "enabled": True},
        {"host": "claude", "registered": True, "enabled": True},
    ]
    monkeypatch.setattr(
        "agency_runtime.core.installer.inspect_host_installations", lambda: inventory
    )
    assert inspect_host_status(store, "codex")["effective_enabled"] is False
    assert inspect_host_status(store, "claude")["effective_enabled"] is True
    statuses = inspect_all_host_statuses(store)
    assert [item["host"] for item in statuses] == list(SUPPORTED_HOSTS)


def test_stickiness_handles_empty_expired_context_and_similarity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stickiness.clear_session_routing()
    assert stickiness.session_check("", "task") is None
    stickiness.session_put("", "task", {"selected_ids": ["ignored"]})

    now = {"value": 10.0}
    monkeypatch.setattr(stickiness.time, "monotonic", lambda: now["value"])
    stickiness.session_put(
        "session",
        "security review",
        {"selected_ids": ["security", "stale"]},
        context_fingerprint="one",
    )
    assert stickiness.session_check("session", "security review", context_fingerprint="two") is None
    assert stickiness.session_check("session", "", context_fingerprint="one") is None
    assert stickiness.session_check("session", "unrelated task", context_fingerprint="one") is None
    reused = stickiness.session_check(
        "session",
        "security review",
        context_fingerprint="one",
        valid_ids={"security"},
    )
    assert reused is not None
    assert reused["selected_ids"] == ["security"]
    now["value"] = 20.0
    assert stickiness.session_check("session", "security review", max_age=1) is None


def test_intent_and_explain_helpers_cover_validation_and_empty_terms() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        mask_excluded_intent(1)  # type: ignore[arg-type]
    masked = mask_excluded_intent("keep this; not remove\nkeep newline")
    assert "\n" in masked
    assert _clamp_limit("invalid") == 10  # type: ignore[arg-type]
    assert _clamp_limit(1000) == 50
    assert _agent_summary(None) == {
        "slug": "",
        "name": "",
        "division": "",
        "description": "",
        "selected": False,
    }
    assert _domain_terms("task", "task [domain context: security, , performance]") == [
        "security",
        "performance",
    ]
    assert _domain_terms("same", "same") == []
