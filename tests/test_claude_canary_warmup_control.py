"""Bootstrap suppression is native-session-only, not a private-control fiction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agency_runtime.core import canary
from agency_runtime.core.canary_backends import SafeClaudeCanaryBackend
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.runtime_control import read_authoritative_runtime_control


def _backend(tmp_path, *, enabled=True, fail_at=None):
    auth = tmp_path / "auth" / ".credentials.json"
    auth.parent.mkdir(mode=0o700)
    auth.write_text('{"token":"fixture-not-a-real-credential"}')
    auth.chmod(0o600)
    plugin = tmp_path / "marketplace" / "plugins" / "agency-preflight"
    plugin.mkdir(parents=True)
    calls = []

    def runner(argv, **kwargs):
        state, transport = read_authoritative_runtime_control(
            path=kwargs["env"]["AGENCY_CANARY_CONTROL_PATH"], use_cache=False
        )
        assert transport == "direct"
        calls.append({"argv": list(argv), "enabled": state["enabled"], **kwargs})
        if fail_at == len(calls):
            return BoundedProcessResult(1, "", "")
        if argv[1:3] == ["plugin", "install"]:
            target = Path(kwargs["env"]["CLAUDE_CONFIG_DIR"]) / "plugins"
            target.mkdir()
            (target / "installed_plugins.json").write_text(
                json.dumps({"plugins": {"agency-preflight@agency-runtime": [{}]}})
            )
        return BoundedProcessResult(0, json.dumps({"result": "fixture response"}), "")

    backend = SafeClaudeCanaryBackend(
        executable="fixture-claude",
        db_path=tmp_path / "agency.db",
        timeout=10,
        plugin_dir=plugin,
        auth_source=auth,
        process_runner=runner,
        source_env={"HOME": str(tmp_path / "owner-home")},
        master_enabled=enabled,
    )
    return backend, calls


@pytest.mark.parametrize("enabled", [True, False])
def test_only_warmup_uses_native_session_hook_suppression(tmp_path, enabled):
    backend, calls = _backend(tmp_path, enabled=enabled)
    result = backend.execute(task="nonce-bound fixture", workdir=str(tmp_path))
    assert result["status"] == "completed"
    assert [call["enabled"] for call in calls] == [enabled] * 4
    warmup = calls[2]["argv"]
    assert json.loads(warmup[warmup.index("--settings") + 1]) == {"disableAllHooks": True}
    assert all("--settings" not in calls[index]["argv"] for index in (0, 1, 3))
    assert calls[2]["input_text"] == "Reply with one word: ok"
    assert calls[3]["input_text"] == "nonce-bound fixture"
    assert calls[3]["env"]["AGENCY_CANARY_MASTER_ENABLED"] == str(int(enabled))
    assert "--tools=Agent" in calls[3]["argv"]
    assert "--permission-mode" in calls[3]["argv"]
    assert "dontAsk" in calls[3]["argv"]
    assert all(0 < call["timeout"] <= 10 for call in calls)
    assert result["isolated_plugin"]["registered"] is True
    assert not (tmp_path / "owner-home").exists()
    assert not Path(calls[0]["env"]["CLAUDE_CONFIG_DIR"]).exists()


@pytest.mark.parametrize("fail_at", [1, 2, 3])
def test_failed_bootstrap_never_launches_nonce_request(tmp_path, fail_at):
    backend, calls = _backend(tmp_path, fail_at=fail_at)
    result = backend.execute(task="nonce-bound fixture", workdir=str(tmp_path))
    assert result["status"] == "failed"
    assert len(calls) == fail_at
    assert not any(call.get("input_text") == "nonce-bound fixture" for call in calls)


def test_unverified_private_control_still_fails_closed_before_launch(tmp_path, monkeypatch):
    backend, calls = _backend(tmp_path)

    def project(*args, **kwargs):
        raise RuntimeError("isolated canary runtime control projection failed")

    monkeypatch.setattr(canary, "_project_isolated_runtime_control", project)
    with pytest.raises(RuntimeError, match="control projection failed"):
        backend.execute(task="nonce-bound fixture", workdir=str(tmp_path))
    assert not calls


def test_generated_owner_bound_hooks_do_not_supply_warmup_isolation(tmp_path):
    from agency_runtime.core.installer_payloads import _claude_hooks

    owner_control = tmp_path / "owner-control.json"
    hooks = _claude_hooks(60, runtime_control_path_value=str(owner_control))
    commands = [
        [hook["command"], *hook["args"]]
        for matchers in hooks["hooks"].values()
        for matcher in matchers
        for hook in matcher["hooks"]
    ]
    assert commands and all("--runtime-control" in command for command in commands)
    assert all(str(owner_control) in command for command in commands)
    backend, calls = _backend(tmp_path)
    backend.execute(task="nonce-bound fixture", workdir=str(tmp_path))
    # The generated commands still point at the owner. Only the supported
    # host-session setting suppresses their launch during bootstrap; private
    # control state is not evidence that bound hooks would be disabled.
    assert all(call["enabled"] is True for call in calls)
    warmup = calls[2]["argv"]
    assert warmup[warmup.index("--settings") + 1] == '{"disableAllHooks":true}'
    assert "--settings" not in calls[3]["argv"]
