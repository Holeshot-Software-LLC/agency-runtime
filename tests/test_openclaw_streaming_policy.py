from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from agency_runtime.core.installer_contracts import NativeCommandResult
from agency_runtime.core.openclaw_streaming_policy import (
    _digest,
    _effective_config_identity,
    _parse_snapshot,
    _read_backup,
    _render_path,
    _streaming_paths,
    _validate_backup,
    backup_path,
    enforce_final_only_delivery,
    restore_prior_delivery,
    retained_backup_status,
)


class _ConfigRunner:
    def __init__(
        self,
        snapshot: dict[str, Any],
        *,
        fail_set: int | None = None,
        ignore_set: int | None = None,
        fail_rollback: bool = False,
    ) -> None:
        self.snapshot = copy.deepcopy(snapshot)
        self.fail_set = fail_set
        self.ignore_set = ignore_set
        self.fail_rollback = fail_rollback
        self.commands: list[tuple[str, list[str]]] = []
        self.set_count = 0
        paths = set(_streaming_paths(self.snapshot))
        paths.update(
            prefix
            for path in tuple(paths)
            for prefix in (path[:-1], path[:-2])
            if prefix[-1] in {"streaming", "block"}
        )
        self.known_paths = {_render_path(path): path for path in paths}

    def _result(
        self,
        command: list[str],
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> NativeCommandResult:
        return NativeCommandResult(tuple(command), returncode, stdout, stderr)

    def _write(self, path: tuple[str, ...], value: Any) -> None:
        node = self.snapshot
        for part in path[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[path[-1]] = value

    def _unset(self, path: tuple[str, ...]) -> None:
        node: Any = self.snapshot
        for part in path[:-1]:
            if not isinstance(node, dict) or not isinstance(node.get(part), dict):
                return
            node = node[part]
        if isinstance(node, dict):
            node.pop(path[-1], None)

    def __call__(self, name: str, command: list[str]) -> NativeCommandResult:
        self.commands.append((name, list(command)))
        if command[1:4] == ["config", "get", "agents.defaults"]:
            return self._result(command, stdout=json.dumps(self.snapshot["agents"]["defaults"]))
        if command[1:4] == ["config", "get", "channels"]:
            return self._result(command, stdout=json.dumps(self.snapshot["channels"]))
        path = self.known_paths[command[3]]
        if command[2] == "set":
            is_rollback = "rollback" in name
            if is_rollback and self.fail_rollback:
                return self._result(command, returncode=30, stderr="read-only file system")
            if not is_rollback:
                self.set_count += 1
                if self.set_count == self.fail_set:
                    return self._result(command, returncode=30, stderr="read-only file system")
                if self.set_count == self.ignore_set:
                    return self._result(command)
            self._write(path, json.loads(command[4]))
            return self._result(command)
        if "rollback" in name and self.fail_rollback:
            return self._result(command, returncode=30, stderr="read-only file system")
        self._unset(path)
        return self._result(command)


def _snapshot() -> dict[str, Any]:
    return {
        "agents": {
            "defaults": {
                "blockStreamingDefault": "on",
                "model": "provider/model",
            }
        },
        "channels": {
            "defaults": {"groupPolicy": "allowlist"},
            "modelByChannel": {},
            "telegram": {
                "botToken": "redacted-secret",
                "streaming": {"mode": "partial", "block": {"enabled": True}},
                "accounts": {
                    "ops.prod": {
                        "botToken": "another-secret",
                        "streaming": {"mode": "block", "block": {"enabled": True}},
                    }
                },
            },
            "whatsapp": {
                "streaming": {"block": {"enabled": True}},
                "accounts": {"default": {}},
            },
            "qqbot": {"streaming": {"mode": "partial"}},
            "irc": {"enabled": True, "password": "never-persist-this"},
        },
    }


def test_final_only_policy_is_transactional_redacted_and_idempotent(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())

    first = enforce_final_only_delivery(runner, runtime_home=tmp_path)

    assert first["ok"] is True
    assert first["changed"] == 8
    assert first["managed_paths"] == 8
    assert first["idempotent"] is False
    assert runner.snapshot["agents"]["defaults"]["blockStreamingDefault"] == "off"
    telegram = runner.snapshot["channels"]["telegram"]
    assert telegram["streaming"] == {"mode": "off", "block": {"enabled": False}}
    assert telegram["accounts"]["ops.prod"]["streaming"] == {
        "mode": "off",
        "block": {"enabled": False},
    }
    assert runner.snapshot["channels"]["whatsapp"]["streaming"]["block"] == {"enabled": False}
    assert runner.snapshot["channels"]["whatsapp"]["accounts"]["default"]["streaming"]["block"] == {
        "enabled": False
    }
    assert runner.snapshot["channels"]["qqbot"]["streaming"]["mode"] == "off"
    assert any('["ops.prod"]' in " ".join(command) for _name, command in runner.commands)

    backup = Path(first["backup_path"])
    raw_backup = backup.read_text(encoding="utf-8")
    assert "redacted-secret" not in raw_backup
    assert "another-secret" not in raw_backup
    assert "never-persist-this" not in raw_backup
    original = yaml.safe_load(raw_backup)
    original_global = next(
        entry
        for entry in original["entries"]
        if entry["path"] == ["agents", "defaults", "blockStreamingDefault"]
    )
    assert original_global["value"] == "on"

    repeat_start = len(runner.commands)
    second = enforce_final_only_delivery(runner, runtime_home=tmp_path)

    assert second["ok"] is True
    assert second["changed"] == 0
    assert second["idempotent"] is True
    assert not any(
        command[1:3] in (["config", "set"], ["config", "unset"])
        for _name, command in runner.commands[repeat_start:]
    )
    repeated = yaml.safe_load(backup.read_text(encoding="utf-8"))
    repeated_global = next(
        entry
        for entry in repeated["entries"]
        if entry["path"] == ["agents", "defaults", "blockStreamingDefault"]
    )
    assert repeated_global["value"] == "on"
    assert backup.read_text(encoding="utf-8") == raw_backup


def _select_openclaw_identity(
    monkeypatch: pytest.MonkeyPatch,
    **values: str,
) -> None:
    for name in (
        "OPENCLAW_HOME",
        "OPENCLAW_PROFILE",
        "OPENCLAW_STATE_DIR",
        "OPENCLAW_CONFIG_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_backups_and_restores_are_isolated_by_openclaw_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    blue_profile = "private-blue-profile"
    green_profile = "private-green-profile"
    blue_original = _snapshot()
    green_original = _snapshot()
    green_original["agents"]["defaults"]["blockStreamingDefault"] = "green-prior"
    green_original["channels"]["telegram"]["streaming"]["mode"] = "green-preview"
    blue = _ConfigRunner(blue_original)
    green = _ConfigRunner(green_original)

    _select_openclaw_identity(monkeypatch, OPENCLAW_PROFILE=blue_profile)
    blue_result = enforce_final_only_delivery(blue, runtime_home=tmp_path)
    _select_openclaw_identity(monkeypatch, OPENCLAW_PROFILE=green_profile)
    green_result = enforce_final_only_delivery(green, runtime_home=tmp_path)

    blue_path = Path(blue_result["backup_path"])
    green_path = Path(green_result["backup_path"])
    assert blue_result["ok"] is True
    assert green_result["ok"] is True
    assert blue_path != green_path
    assert blue_profile not in str(blue_path)
    assert green_profile not in str(green_path)
    assert blue_profile not in blue_path.read_text(encoding="utf-8")
    assert green_profile not in green_path.read_text(encoding="utf-8")

    assert restore_prior_delivery(green, runtime_home=tmp_path)["ok"] is True
    assert green.snapshot == green_original
    _select_openclaw_identity(monkeypatch, OPENCLAW_PROFILE=blue_profile)
    assert restore_prior_delivery(blue, runtime_home=tmp_path)["ok"] is True
    assert blue.snapshot == blue_original


def test_backup_namespace_covers_every_effective_openclaw_path_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private_home = tmp_path.parent / "private-openclaw-home"
    private_state = tmp_path.parent / "private-openclaw-state"
    private_config = tmp_path.parent / "private-openclaw-config" / "runtime.json"
    environments = (
        {},
        {"OPENCLAW_PROFILE": "profile-identity"},
        {"OPENCLAW_HOME": str(private_home)},
        {"OPENCLAW_STATE_DIR": str(private_state)},
        {"OPENCLAW_CONFIG_PATH": str(private_config)},
    )
    paths: list[Path] = []
    for environment in environments:
        _select_openclaw_identity(monkeypatch, **environment)
        paths.append(backup_path(tmp_path))

    assert len(set(paths)) == len(environments)
    rendered = json.dumps([str(path) for path in paths])
    assert "profile-identity" not in rendered
    assert private_home.name not in rendered
    assert private_state.name not in rendered
    assert private_config.parent.name not in rendered

    _select_openclaw_identity(monkeypatch)
    default_path = backup_path(tmp_path)
    _select_openclaw_identity(monkeypatch, OPENCLAW_PROFILE="default")
    assert backup_path(tmp_path) == default_path

    with pytest.raises(ValueError, match="config identity is invalid"):
        backup_path(tmp_path, config_identity="not-a-digest")


def test_caller_environment_is_the_authoritative_config_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _select_openclaw_identity(monkeypatch, OPENCLAW_PROFILE="process-profile")
    environment = {
        "OPENCLAW_PROFILE": "command-profile",
        "OPENCLAW_STATE_DIR": " ",
    }
    expected_identity = _effective_config_identity(environment)
    runner = _ConfigRunner(_snapshot())

    result = enforce_final_only_delivery(
        runner,
        runtime_home=tmp_path,
        environment=environment,
    )

    assert result["ok"] is True
    assert Path(result["backup_path"]) == backup_path(
        tmp_path,
        config_identity=expected_identity,
    )
    assert Path(result["backup_path"]) != backup_path(tmp_path)
    assert "command-profile" not in json.dumps(result)


def test_copied_backup_is_rejected_for_a_different_profile_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _select_openclaw_identity(monkeypatch, OPENCLAW_PROFILE="source-profile")
    runner = _ConfigRunner(_snapshot())
    source = enforce_final_only_delivery(runner, runtime_home=tmp_path)
    source_path = Path(source["backup_path"])

    _select_openclaw_identity(monkeypatch, OPENCLAW_PROFILE="target-profile")
    target_path = backup_path(tmp_path)
    target_path.parent.mkdir(parents=True)
    target_path.write_bytes(source_path.read_bytes())

    status = retained_backup_status(runtime_home=tmp_path)
    restored = restore_prior_delivery(runner, runtime_home=tmp_path)

    assert status["backup_state"] == "invalid"
    assert restored["ok"] is False
    assert "different config identity" in restored["error"]
    public = json.dumps({"status": status, "restore": restored})
    assert "source-profile" not in public
    assert "target-profile" not in public


def test_final_only_policy_rolls_back_partial_write_failure(tmp_path: Path) -> None:
    original = _snapshot()
    runner = _ConfigRunner(original, fail_set=3)

    result = enforce_final_only_delivery(runner, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["rollback_attempted"] is True
    assert result["rollback_verified"] is True
    assert result["error"] == "OpenClaw final-only config write failed"
    assert "read-only file system" not in json.dumps(result)
    assert "Nix-managed or immutable" in result["recovery"]
    assert runner.snapshot == original
    assert any("rollback" in name for name, _command in runner.commands)


def test_final_only_policy_rolls_back_postcondition_mismatch(tmp_path: Path) -> None:
    original = _snapshot()
    runner = _ConfigRunner(original, ignore_set=2)

    result = enforce_final_only_delivery(runner, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["error"] == "postcondition verification failed"
    assert result["rollback_verified"] is True
    assert runner.snapshot == original


def test_final_only_policy_reports_unproven_rollback_and_retained_backup(
    tmp_path: Path,
) -> None:
    runner = _ConfigRunner(_snapshot(), fail_set=3, fail_rollback=True)

    result = enforce_final_only_delivery(runner, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["rollback_verified"] is False
    assert "Keep the gateway stopped" in result["recovery"]
    status = retained_backup_status(runtime_home=tmp_path)
    assert status["backup_retained"] is True
    assert status["automatic_restore"] is False
    assert "config set/unset" in status["recovery"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda state: state["channels"].__setitem__("telegram", "invalid"),
            "channel 'telegram' config is invalid",
        ),
        (
            lambda state: state["channels"]["telegram"].__setitem__("streaming", True),
            "legacy streaming shape",
        ),
        (
            lambda state: state["channels"]["telegram"].__setitem__("accounts", []),
            "accounts config is invalid",
        ),
        (
            lambda state: state["channels"]["telegram"]["accounts"].__setitem__(
                "ops.prod", "invalid"
            ),
            "account 'ops.prod' is invalid",
        ),
        (
            lambda state: state["agents"]["defaults"].__setitem__(
                "blockStreamingDefault", {"invalid": True}
            ),
            "streaming value",
        ),
    ],
)
def test_final_only_policy_fails_before_mutation_for_invalid_config(
    tmp_path: Path,
    mutate,
    message: str,
) -> None:
    state = _snapshot()
    mutate(state)
    runner = _ConfigRunner.__new__(_ConfigRunner)
    runner.snapshot = copy.deepcopy(state)
    runner.commands = []

    def inspect_only(name: str, command: list[str]) -> NativeCommandResult:
        runner.commands.append((name, command))
        section = (
            runner.snapshot["agents"]["defaults"]
            if command[3] == "agents.defaults"
            else runner.snapshot["channels"]
        )
        return NativeCommandResult(tuple(command), 0, json.dumps(section), "")

    result = enforce_final_only_delivery(inspect_only, runtime_home=tmp_path)

    assert result["ok"] is False
    assert message in result["error"]
    assert result["changed"] == 0
    assert not Path(result["backup_path"]).exists()


def test_final_only_policy_rejects_corrupt_owned_backup(tmp_path: Path) -> None:
    backup = backup_path(tmp_path)
    backup.parent.mkdir(parents=True)
    backup.write_text("schema_version: 999\n", encoding="utf-8")
    runner = _ConfigRunner(_snapshot())

    result = enforce_final_only_delivery(runner, runtime_home=tmp_path)

    assert result["ok"] is False
    assert "invalid schema" in result["error"]
    assert not any(command[1:3] == ["config", "set"] for _name, command in runner.commands)


def test_retained_backup_status_without_backup_is_actionable(tmp_path: Path) -> None:
    status = retained_backup_status(runtime_home=tmp_path)

    assert status["backup_retained"] is False
    assert status["backup_state"] == "missing"
    assert "rerun native Agency installation" in status["recovery"]


def test_restore_prior_delivery_restores_original_shape_and_values(tmp_path: Path) -> None:
    original = _snapshot()
    runner = _ConfigRunner(original)
    assert enforce_final_only_delivery(runner, runtime_home=tmp_path)["ok"] is True

    restored = restore_prior_delivery(runner, runtime_home=tmp_path)

    assert restored["ok"] is True
    assert restored["restored"] is True
    assert restored["final_only_reapplied"] is False
    assert runner.snapshot == original


def test_restore_prior_delivery_compensates_to_final_only_on_failure(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())
    assert enforce_final_only_delivery(runner, runtime_home=tmp_path)["ok"] is True

    def fail_first_restore(name: str, command: list[str]) -> NativeCommandResult:
        suffix = name.removeprefix("streaming_config_restore_")
        if suffix.isdigit():
            return NativeCommandResult(tuple(command), 30, "", "read-only file system")
        return runner(name, command)

    result = restore_prior_delivery(fail_first_restore, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["final_only_reapplied"] is True
    assert runner.snapshot["agents"]["defaults"]["blockStreamingDefault"] == "off"


def test_restore_prior_delivery_reports_unproven_compensation(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())
    assert enforce_final_only_delivery(runner, runtime_home=tmp_path)["ok"] is True

    def fail_restore_and_compensation(name: str, command: list[str]) -> NativeCommandResult:
        suffix = name.removeprefix("streaming_config_restore_")
        if suffix.isdigit() or suffix.startswith("compensate_"):
            return NativeCommandResult(tuple(command), 30, "", "read-only file system")
        return runner(name, command)

    result = restore_prior_delivery(fail_restore_and_compensation, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["final_only_reapplied"] is False
    assert "Neither prior-value restoration" in result["recovery"]


def test_restore_is_idempotent_and_skips_already_absent_containers(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())
    assert enforce_final_only_delivery(runner, runtime_home=tmp_path)["ok"] is True
    assert restore_prior_delivery(runner, runtime_home=tmp_path)["ok"] is True

    repeated = restore_prior_delivery(runner, runtime_home=tmp_path)

    assert repeated["ok"] is True
    assert repeated["changed"] == 0


def test_restore_compensates_when_container_cleanup_fails(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())
    assert enforce_final_only_delivery(runner, runtime_home=tmp_path)["ok"] is True

    def fail_cleanup(name: str, command: list[str]) -> NativeCommandResult:
        if name.startswith("streaming_config_restore_container_"):
            return NativeCommandResult(tuple(command), 30, "", "read-only file system")
        return runner(name, command)

    result = restore_prior_delivery(fail_cleanup, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["final_only_reapplied"] is True


@pytest.mark.parametrize("mode", ["inspection", "mismatch"])
def test_restore_compensates_when_final_verification_is_unavailable_or_mismatched(
    tmp_path: Path,
    mode: str,
) -> None:
    runner = _ConfigRunner(_snapshot())
    assert enforce_final_only_delivery(runner, runtime_home=tmp_path)["ok"] is True
    ignored = False

    def disrupt_verify(name: str, command: list[str]) -> NativeCommandResult:
        nonlocal ignored
        if mode == "inspection" and name == "streaming_config_restore_after_agents":
            return NativeCommandResult(tuple(command), 1, "", "inspection unavailable")
        suffix = name.removeprefix("streaming_config_restore_")
        if mode == "mismatch" and suffix.isdigit() and not ignored:
            ignored = True
            return NativeCommandResult(tuple(command), 0, "", "")
        return runner(name, command)

    result = restore_prior_delivery(disrupt_verify, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["final_only_reapplied"] is True


def test_restore_skips_cleanup_for_container_already_absent(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())
    assert enforce_final_only_delivery(runner, runtime_home=tmp_path)["ok"] is True
    runner.snapshot["channels"]["whatsapp"]["accounts"]["default"].pop("streaming")

    result = restore_prior_delivery(runner, runtime_home=tmp_path)

    assert result["ok"] is True


def test_restore_prior_delivery_requires_valid_covering_backup(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())
    missing = restore_prior_delivery(runner, runtime_home=tmp_path)
    assert missing["ok"] is False
    assert "backup is missing" in missing["error"]

    minimal = {
        "agents": {"defaults": {}},
        "channels": {},
    }
    minimal_runner = _ConfigRunner(minimal)
    assert enforce_final_only_delivery(minimal_runner, runtime_home=tmp_path)["ok"] is True
    runner.snapshot["agents"]["defaults"]["blockStreamingDefault"] = "off"
    uncovered = restore_prior_delivery(runner, runtime_home=tmp_path)

    assert uncovered["ok"] is False
    assert "does not cover the active policy" in uncovered["error"]


def test_retained_backup_status_rejects_corrupt_backup(tmp_path: Path) -> None:
    path = backup_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("invalid: true\n", encoding="utf-8")

    status = retained_backup_status(runtime_home=tmp_path)

    assert status["backup_retained"] is False
    assert status["backup_state"] == "invalid"


def _valid_backup() -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": 2,
        "kind": "openclaw-final-only-streaming-values",
        "config_identity": _effective_config_identity(),
        "created_at": "2026-07-15T00:00:00+00:00",
        "updated_at": "2026-07-15T00:00:00+00:00",
        "entries": [],
        "containers": [],
    }
    document["sha256"] = _digest(document)
    return document


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.__setitem__("entries", None), "entries are invalid"),
        (lambda value: value["entries"].append({}), "entry is invalid"),
        (
            lambda value: value["entries"].append({"path": [], "present": False, "value": None}),
            "path is invalid",
        ),
        (
            lambda value: value["entries"].append(
                {"path": ["channels", "telegram", "token"], "present": False, "value": None}
            ),
            "not an owned streaming leaf",
        ),
        (
            lambda value: value["entries"].append(
                {"path": ["channels", "telegram", "streaming", "mode"], "present": 1, "value": None}
            ),
            "presence flag is invalid",
        ),
        (
            lambda value: value["entries"].append(
                {
                    "path": ["channels", "telegram", "streaming", "mode"],
                    "present": True,
                    "value": {},
                }
            ),
            "backup value is invalid",
        ),
        (
            lambda value: value["entries"].append(
                {
                    "path": ["channels", "telegram", "streaming", "mode"],
                    "present": False,
                    "value": "off",
                }
            ),
            "absent value must be null",
        ),
        (lambda value: value.__setitem__("containers", None), "containers are invalid"),
        (lambda value: value["containers"].append({}), "container is invalid"),
        (
            lambda value: value["containers"].append({"path": [], "present": False}),
            "container path is invalid",
        ),
        (
            lambda value: value["containers"].append(
                {"path": ["channels", "telegram", "accounts"], "present": False}
            ),
            "container is invalid",
        ),
        (lambda value: value.__setitem__("schema_version", 999), "version is unsupported"),
        (lambda value: value.__setitem__("kind", "wrong"), "kind is invalid"),
        (lambda value: value.__setitem__("config_identity", "wrong"), "identity is invalid"),
        (lambda value: value.__setitem__("created_at", 1), "timestamp is invalid"),
        (lambda value: value.__setitem__("sha256", "wrong"), "integrity check failed"),
    ],
)
def test_streaming_backup_validation_rejects_every_malformed_surface(
    mutate,
    message: str,
) -> None:
    document = _valid_backup()
    mutate(document)
    if message != "integrity check failed":
        document["sha256"] = _digest(document)

    with pytest.raises(ValueError, match=message):
        _validate_backup(document)


def test_streaming_backup_rejects_link_like_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "backup.yaml"
    path.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(
        "agency_runtime.core.openclaw_streaming_policy.is_link_or_reparse_point",
        lambda _path: True,
    )

    with pytest.raises(ValueError, match="symlink or reparse point"):
        _read_backup(path)


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (NativeCommandResult(("openclaw",), 1, "", "denied"), "inspection failed"),
        (NativeCommandResult(("openclaw",), 0, "not-json", ""), "not bounded JSON"),
        (NativeCommandResult(("openclaw",), 0, "[]", ""), "was not an object"),
    ],
)
def test_streaming_snapshot_parser_fails_closed(
    result: NativeCommandResult,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _parse_snapshot(result, "channels")


def test_streaming_path_discovery_validates_root_ids_and_null_channel() -> None:
    with pytest.raises(ValueError, match="channels config is invalid"):
        _streaming_paths({"channels": []})
    with pytest.raises(ValueError, match="channel id is invalid"):
        _streaming_paths({"channels": {1: {}}})

    desired = _streaming_paths({"channels": {"telegram": None}})

    assert desired[("channels", "telegram", "streaming", "mode")] == "off"
    assert desired[("channels", "telegram", "streaming", "block", "enabled")] is False


def test_streaming_path_discovery_rejects_empty_account_id() -> None:
    with pytest.raises(ValueError, match="account id is invalid"):
        _streaming_paths({"channels": {"telegram": {"accounts": {"": {}}}}})


def test_policy_rolls_back_when_successful_writes_cannot_be_reinspected(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot())

    def fail_after(name: str, command: list[str]) -> NativeCommandResult:
        if name == "streaming_config_after_agents":
            return NativeCommandResult(tuple(command), 1, "", "inspect unavailable")
        return runner(name, command)

    result = enforce_final_only_delivery(fail_after, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["rollback_verified"] is True


def test_policy_reports_when_rollback_snapshot_is_unavailable(tmp_path: Path) -> None:
    runner = _ConfigRunner(_snapshot(), fail_set=2)

    def fail_rollback_read(name: str, command: list[str]) -> NativeCommandResult:
        if name == "streaming_config_rollback_agents":
            return NativeCommandResult(tuple(command), 1, "", "inspect unavailable")
        return runner(name, command)

    result = enforce_final_only_delivery(fail_rollback_read, runtime_home=tmp_path)

    assert result["ok"] is False
    assert result["rollback_verified"] is False
