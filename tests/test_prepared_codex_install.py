"""Focused contracts for the exact prepared Codex refresh coordinator."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.cli import main as cli_main
from agency_runtime.cli.install_commands import InstallDependencies, cmd_install
from agency_runtime.core import installer_filesystem, installer_inventory, operator_presence
from agency_runtime.core import prepared_codex_install as prepared_install
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer_contracts import INSTALL_MANIFEST, NativeCommandResult


def _digest(character: str) -> str:
    return character * 64


def test_path_key_never_expands_noncanonical_inventory_text(tmp_path: Path) -> None:
    target = tmp_path / "marketplace"

    assert prepared_install._path_key(target) == os.path.normcase(str(target.resolve()))
    assert prepared_install._path_key("~/marketplace") == ""
    assert prepared_install._path_key("relative/marketplace") == ""


def _binding(
    tmp_path: Path,
    **overrides: str | int,
) -> prepared_install._CodexInstallBinding:
    values: dict[str, str | int] = {
        "action": prepared_install._ACTION,
        "host": "codex",
        "config_path": str((tmp_path / "agency.yaml").resolve()),
        "config_revision": "sha256:" + _digest("1"),
        "database_path": str((tmp_path / "agency.db").resolve()),
        "database_device": 10,
        "database_inode": 20,
        "roster_generation": 30,
        "host_control_generation": 40,
        "runtime_control_generation": 50,
        "target_path": str((tmp_path / "marketplace").resolve()),
        "target_parent_device": 60,
        "target_parent_inode": 70,
        "current_install_id": "install-current",
        "current_plugin_version": "0.1.0",
        "candidate_plugin_version": "0.2.0",
        "current_bundle_sha256": _digest("2"),
        "current_tree_sha256": _digest("3"),
        "candidate_plan_sha256": _digest("4"),
        "launcher_plan_sha256": _digest("5"),
        "codex_executable_path": str((tmp_path / "codex.exe").resolve()),
        "codex_executable_sha256": _digest("6"),
        "codex_executable_identity_sha256": _digest("7"),
        "codex_environment_sha256": _digest("8"),
        "codex_version": "codex-cli 0.145.0",
        "marketplace_state_sha256": _digest("9"),
        "plugin_state_sha256": _digest("a"),
    }
    values.update(overrides)
    return prepared_install._make_binding(**values)


def _prepared(
    tmp_path: Path,
    *,
    binding: prepared_install._CodexInstallBinding | None = None,
) -> SimpleNamespace:
    frozen = binding or _binding(tmp_path)
    native = prepared_install._CodexNativeState(
        plugin_present=True,
        plugin_enabled=True,
        plugin_version=frozen.current_plugin_version,
        plugin_state_sha256=frozen.plugin_state_sha256,
        marketplace_state_sha256=frozen.marketplace_state_sha256,
    )
    return SimpleNamespace(
        binding=frozen,
        config=AgencyConfig(config_path=frozen.config_path),
        target=Path(frozen.target_path),
        target_snapshot=prepared_install._ManagedTargetSnapshot(
            install_id=frozen.current_install_id,
            plugin_version=frozen.current_plugin_version,
            bundle_sha256=frozen.current_bundle_sha256,
            tree_sha256=frozen.current_tree_sha256,
            parent_device=frozen.target_parent_device,
            parent_inode=frozen.target_parent_inode,
        ),
        runtime_plan=SimpleNamespace(),
        component_files={},
        primary_file="plugins/agency-preflight/.codex-plugin/plugin.json",
        python_identity=SimpleNamespace(),
        codex_argv=SimpleNamespace(),
        codex_environment={},
        native_state=native,
        runtime_control=SimpleNamespace(),
    )


def _installed_snapshot(
    prepared: SimpleNamespace,
    *,
    plugin_version: str | None = None,
    bundle_sha256: str | None = None,
    tree_sha256: str | None = None,
) -> prepared_install._ManagedTargetSnapshot:
    return prepared_install._ManagedTargetSnapshot(
        install_id="installed-id",
        # The on-disk install manifest carries the public Agency plugin
        # version; the Codex-native inventory carries the cache-busted
        # ``+codex.<digest>`` candidate version.
        plugin_version=plugin_version or prepared_install.PLUGIN_VERSION,
        bundle_sha256=bundle_sha256 or _digest("f"),
        tree_sha256=tree_sha256 or _digest("0"),
        parent_device=prepared.target_snapshot.parent_device,
        parent_inode=prepared.target_snapshot.parent_inode,
    )


def _successful_native_result(arguments: tuple[str, ...]) -> NativeCommandResult:
    return NativeCommandResult(arguments, 0, "{}", "")


def _native_inventory_results(
    target: Path,
    *,
    installed_rows: list[object] | None = None,
    available_rows: list[object] | None = None,
    marketplace_rows: list[object] | None = None,
    inventory_extra: bool = False,
) -> tuple[NativeCommandResult, NativeCommandResult]:
    plugin = {
        "pluginId": prepared_install._SELECTOR,
        "name": "agency-preflight",
        "marketplaceName": "agency-runtime",
        "version": "0.1.0+codex.0123456789ab",
        "installed": True,
        "enabled": True,
        "source": {
            "source": "local",
            "path": str(target / "plugins" / "agency-preflight"),
        },
        "marketplaceSource": {"sourceType": "local", "source": str(target)},
        "installPolicy": "AVAILABLE",
        "authPolicy": "ON_INSTALL",
    }
    inventory: dict[str, object] = {
        "installed": [plugin] if installed_rows is None else installed_rows,
        "available": [] if available_rows is None else available_rows,
    }
    if inventory_extra:
        inventory["unexpected"] = []
    marketplaces = {
        "marketplaces": (
            [{"name": "agency-runtime", "root": str(target)}]
            if marketplace_rows is None
            else marketplace_rows
        )
    }
    return (
        NativeCommandResult((), 0, json.dumps(inventory), ""),
        NativeCommandResult((), 0, json.dumps(marketplaces), ""),
    )


def _run_refresh_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    prepared: SimpleNamespace,
    snapshots: list[prepared_install._ManagedTargetSnapshot],
    atomic_error: Exception | None = None,
    fail_launcher_revalidation_at: int | None = None,
) -> tuple[dict[str, Any], list[object]]:
    absent = prepared_install._CodexNativeState(
        False,
        None,
        "",
        _digest("b"),
        prepared.native_state.marketplace_state_sha256,
    )
    final = prepared_install._CodexNativeState(
        True,
        True,
        prepared.binding.candidate_plugin_version,
        _digest("c"),
        prepared.native_state.marketplace_state_sha256,
    )
    native_states = iter((prepared.native_state, absent, final))
    target_snapshots = iter(snapshots)
    events: list[object] = []
    launcher_revalidations = 0

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        yield

    def revalidate(_identities: object) -> None:
        nonlocal launcher_revalidations
        launcher_revalidations += 1
        events.append(("launcher_revalidate", launcher_revalidations))
        if launcher_revalidations == fail_launcher_revalidation_at:
            raise prepared_install.PreparedCodexInstallError("launcher identity drift")

    def strict_state(*_args: object, **_kwargs: object) -> prepared_install._CodexNativeState:
        state = next(native_states)
        events.append(("native_state", state.plugin_version, state.plugin_present))
        return state

    def native_command(
        _prepared: SimpleNamespace,
        arguments: list[str],
        *,
        name: str,
        steps: list[dict[str, Any]],
        timeout: float = 30,
    ) -> NativeCommandResult:
        del _prepared, timeout
        events.append(("native_command", name))
        result = _successful_native_result(tuple(arguments))
        steps.append({"name": name, **result.to_dict()})
        return result

    def install_tree(*_args: object, **_kwargs: object) -> dict[str, Any]:
        events.append("atomic_install")
        if atomic_error is not None:
            raise atomic_error
        return {
            "backup_path": str(tmp_path / "backup"),
            "bundle_digest": _digest("f"),
            "changed": True,
        }

    def target_snapshot(_target: Path) -> prepared_install._ManagedTargetSnapshot:
        value = next(target_snapshots)
        events.append(("target_snapshot", value.tree_sha256))
        return value

    def compensate(*_args: object, **_kwargs: object) -> dict[str, Any]:
        events.append("compensation")
        return {
            "compensated": False,
            "manual_recovery_required": True,
            "error": "test compensation stopped",
        }

    monkeypatch.setattr(prepared_install, "_prepare", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: False)
    monkeypatch.setattr(
        prepared_install,
        "_verify_codex_install_operator_presence",
        lambda _binding: None,
    )
    monkeypatch.setattr(prepared_install, "_install_lock", lock)
    monkeypatch.setattr(prepared_install, "load_config", lambda *_args, **_kwargs: prepared.config)
    monkeypatch.setattr(
        prepared_install,
        "_published_candidate",
        lambda *_args, **_kwargs: ({"candidate": "bytes"}, (object(),)),
    )
    monkeypatch.setattr(prepared_install, "revalidate_persistent_artifacts", revalidate)
    monkeypatch.setattr(prepared_install, "_strict_native_state", strict_state)
    monkeypatch.setattr(prepared_install, "_require_frozen_target", lambda *_args: None)
    monkeypatch.setattr(prepared_install, "atomic_install_tree", install_tree)
    monkeypatch.setattr(prepared_install, "_target_snapshot", target_snapshot)
    monkeypatch.setattr(prepared_install, "_native_command", native_command)
    monkeypatch.setattr(prepared_install, "_compensate", compensate)
    monkeypatch.setattr(prepared_install, "_frozen_backup_error", lambda *_args: None)

    return prepared_install.refresh_existing_codex_adapter(prepared.config), events


@pytest.mark.parametrize(
    "argv",
    [
        ["install", "--agent", "codex", "--no-dashboard"],
        ["install", "--agent", "codex", "--no-dashboard", "--json"],
    ],
)
def test_exact_cli_shapes_delegate_to_the_prepared_coordinator(argv: list[str]) -> None:
    args = cli_main.build_parser().parse_args(argv)

    assert args._operator_presence_prepared_action == prepared_install._ACTION
    assert prepared_install.is_exact_prepared_codex_install(args) is True
    assert operator_presence.request_for_namespace(args) is None


@pytest.mark.parametrize(
    "argv",
    [
        ["install"],
        ["install", "--agent", "codex"],
        ["install", "--agent", "claude", "--no-dashboard"],
        ["install", "--all", "--no-dashboard"],
        ["install", "--agent", "codex", "--no-dashboard", "--profile", "standard"],
        ["install", "--agent", "codex", "--no-dashboard", "--dry-run"],
        ["install", "--agent", "codex", "--no-dashboard", "--rollback"],
        ["install", "--agent", "codex", "--no-dashboard", "--verify-activation"],
        ["install", "--agent", "codex", "--no-dashboard", "--backup", "retained"],
        ["install", "--agent", "codex", "--no-dashboard", "--activation-timeout", "181"],
        ["install", "--agent", "codex", "--no-dashboard", "--activation-timeout", "nan"],
    ],
)
def test_every_nearby_install_shape_is_rejected_from_the_prepared_slice(
    argv: list[str],
) -> None:
    args = cli_main.build_parser().parse_args(argv)

    assert prepared_install.is_exact_prepared_codex_install(args) is False


def test_non_dry_run_near_miss_retains_generic_operator_presence() -> None:
    args = cli_main.build_parser().parse_args(["install", "--agent", "codex"])

    request = operator_presence.request_for_namespace(args)

    assert request is not None
    assert request.family == "installation"


def test_exact_cli_dispatch_does_not_construct_the_generic_store(tmp_path: Path) -> None:
    args = cli_main.build_parser().parse_args(
        ["install", "--agent", "codex", "--no-dashboard", "--json"]
    )
    cfg = AgencyConfig(config_path=str((tmp_path / "agency.yaml").resolve()))
    emitted: list[dict[str, Any]] = []
    calls: list[AgencyConfig] = []

    def install(candidate: AgencyConfig) -> dict[str, Any]:
        calls.append(candidate)
        return {"ok": True, "complete": True, "host": "codex"}

    def forbidden_store(_cfg: AgencyConfig | None) -> object:
        raise AssertionError("prepared refresh must not construct the generic Store")

    exit_code = cmd_install(
        args,
        dependencies=InstallDependencies(
            load_config=lambda: cfg,
            store_factory=forbidden_store,
            emit_json=emitted.append,
            prepared_codex_installer=install,
        ),
    )

    assert exit_code == 0
    assert calls == [cfg]
    assert emitted[0]["roster_action"] == "unchanged_prepared_codex_refresh"
    assert emitted[0]["dashboard"]["status"] == "opted_out"
    assert emitted[0]["transaction_complete"] is True
    assert emitted[0]["activation_complete"] is False
    assert emitted[0]["activation_required"] is True


def test_exact_json_dispatch_contains_config_load_failure_without_claiming_recovery() -> None:
    args = cli_main.build_parser().parse_args(
        ["install", "--agent", "codex", "--no-dashboard", "--json"]
    )
    emitted: list[dict[str, Any]] = []

    def fail_config() -> AgencyConfig:
        raise OSError("config unavailable")

    exit_code = cmd_install(
        args,
        dependencies=InstallDependencies(
            load_config=fail_config,
            emit_json=emitted.append,
        ),
    )

    assert exit_code == 1
    report = emitted[0]
    assert report["ok"] is False
    assert report["profile"] is None
    assert report["transaction_complete"] is False
    assert report["activation_complete"] is False
    assert report["activation_required"] is True
    host = report["hosts"][0]
    assert host["status"] == "failed_before_commit"
    assert host["partial"] is False
    assert host["manual_recovery_required"] is False
    assert host["state_preserved"] is True
    assert "OSError: config unavailable" in host["error"]


def test_exact_json_dispatch_contains_precommit_installer_failure() -> None:
    args = cli_main.build_parser().parse_args(
        ["install", "--agent", "codex", "--no-dashboard", "--json"]
    )
    emitted: list[dict[str, Any]] = []

    def fail_install(_cfg: AgencyConfig) -> dict[str, Any]:
        raise RuntimeError("verification denied")

    exit_code = cmd_install(
        args,
        dependencies=InstallDependencies(
            load_config=AgencyConfig,
            emit_json=emitted.append,
            prepared_codex_installer=fail_install,
        ),
    )

    assert exit_code == 1
    host = emitted[0]["hosts"][0]
    assert host["status"] == "failed_before_commit"
    assert host["partial"] is False
    assert host["manual_recovery_required"] is False
    assert host["state_preserved"] is True


def test_binding_accepts_only_its_exact_type_and_digest(tmp_path: Path) -> None:
    binding = _binding(tmp_path)

    assert prepared_install._codex_install_binding_primitives(binding) == tuple(binding)

    values = list(binding)
    values[binding._fields.index("roster_generation")] = True
    forged_type = prepared_install._CodexInstallBinding(*values)
    with pytest.raises(prepared_install.PreparedCodexInstallError, match="binding is invalid"):
        prepared_install._codex_install_binding_primitives(forged_type)

    forged_digest = binding._replace(binding_sha256=_digest("f"))
    with pytest.raises(prepared_install.PreparedCodexInstallError, match="binding is invalid"):
        prepared_install._codex_install_binding_primitives(forged_digest)

    with pytest.raises(prepared_install.PreparedCodexInstallError, match="binding is invalid"):
        prepared_install._codex_install_binding_primitives(tuple(binding))


def test_strict_native_inventory_accepts_only_complete_object_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "marketplace"
    argv = SimpleNamespace(with_arguments=lambda arguments: arguments)
    results = iter(_native_inventory_results(target))
    monkeypatch.setattr(
        prepared_install,
        "_run_prepared",
        lambda *_args, **_kwargs: next(results),
    )

    state = prepared_install._strict_native_state(
        argv,
        environment={},
        target=target,
    )

    assert state.plugin_present is True
    assert state.plugin_enabled is True
    assert state.plugin_version == "0.1.0+codex.0123456789ab"

    base_inventory_result, base_market_result = _native_inventory_results(target)
    base_inventory = json.loads(base_inventory_result.stdout)
    base_marketplaces = json.loads(base_market_result.stdout)
    malformed: list[tuple[dict[str, object], dict[str, object]]] = []

    installed_scalar = json.loads(base_inventory_result.stdout)
    installed_scalar["installed"].insert(0, 42)
    malformed.append((installed_scalar, base_marketplaces))

    available_scalar = json.loads(base_inventory_result.stdout)
    available_scalar["available"] = ["invalid"]
    malformed.append((available_scalar, base_marketplaces))

    marketplace_scalar = json.loads(base_market_result.stdout)
    marketplace_scalar["marketplaces"].insert(0, "invalid")
    malformed.append((base_inventory, marketplace_scalar))

    inventory_extra = json.loads(base_inventory_result.stdout)
    inventory_extra["unexpected"] = []
    malformed.append((inventory_extra, base_marketplaces))

    marketplace_extra = json.loads(base_market_result.stdout)
    marketplace_extra["unexpected"] = []
    malformed.append((base_inventory, marketplace_extra))

    for inventory, marketplaces in malformed:
        results = iter(
            (
                NativeCommandResult((), 0, json.dumps(inventory), ""),
                NativeCommandResult((), 0, json.dumps(marketplaces), ""),
            )
        )
        with pytest.raises(
            prepared_install.PreparedCodexInstallError,
            match="native inventory schema is invalid",
        ):
            prepared_install._strict_native_state(
                argv,
                environment={},
                target=target,
            )


def test_prepared_codex_process_uses_frozen_executable_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executable_directory = tmp_path / "native-bin"
    executable_directory.mkdir()
    executable = executable_directory / "codex.exe"
    executable.write_bytes(b"reviewed executable placeholder")
    calls: list[dict[str, object]] = []

    class FrozenArgv:
        def __init__(self) -> None:
            self.values = (str(executable), "plugin", "list", "--json")
            self.revalidated = False

        def revalidate(self) -> None:
            self.revalidated = True

        def __getitem__(self, index: int) -> str:
            return self.values[index]

        def __iter__(self):
            return iter(self.values)

    argv = FrozenArgv()

    def run_bounded_process(arguments: object, **kwargs: object) -> SimpleNamespace:
        calls.append({"arguments": tuple(arguments), **kwargs})
        return SimpleNamespace(
            returncode=0,
            stdout="{}",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            timed_out=False,
        )

    monkeypatch.setattr(
        "agency_runtime.core.delegation.backends.run_bounded_process",
        run_bounded_process,
    )

    result = prepared_install._run_prepared(
        argv,
        environment={"CODEX_HOME": str(tmp_path / "profile")},
    )

    assert argv.revalidated is True
    assert result.ok is True
    assert calls[0]["arguments"] == argv.values
    assert calls[0]["cwd"] == str(executable_directory)
    assert calls[0]["env"] == {"CODEX_HOME": str(tmp_path / "profile")}


def test_forced_replacement_retains_backup_and_creates_new_install_lineage(
    tmp_path: Path,
) -> None:
    target = tmp_path / "marketplace"
    files = {"plugins/agency-preflight/plugin.txt": "same candidate bytes\n"}
    first = installer_filesystem.atomic_install_tree(
        target,
        files,
        host="codex",
        dry_run=False,
        home_dir=tmp_path,
    )
    first_manifest = json.loads((target / INSTALL_MANIFEST).read_text(encoding="utf-8"))

    second = installer_filesystem.atomic_install_tree(
        target,
        files,
        host="codex",
        dry_run=False,
        home_dir=tmp_path,
        force_replace=True,
    )

    backup = Path(second["backup_path"])
    second_manifest = json.loads((target / INSTALL_MANIFEST).read_text(encoding="utf-8"))
    backup_manifest = json.loads((backup / INSTALL_MANIFEST).read_text(encoding="utf-8"))
    assert first["backup_path"] is None
    assert second["force_replace"] is True
    assert second["unchanged"] is False
    assert second["would_backup"] is True
    assert backup.is_dir()
    assert backup_manifest["install_id"] == first_manifest["install_id"]
    assert second_manifest["install_id"] != first_manifest["install_id"]
    assert second_manifest["backup_path"] == str(backup)


def test_noop_skips_operator_verification_but_rechecks_under_install_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    events: list[str] = []
    monkeypatch.setattr(prepared_install, "_prepare", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: True)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a no-op must not request operator verification")

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        events.append("lock")
        yield

    monkeypatch.setattr(prepared_install, "_verify_codex_install_operator_presence", forbidden)
    monkeypatch.setattr(prepared_install, "_install_lock", lock)

    result = prepared_install.refresh_existing_codex_adapter(prepared.config)

    assert result["ok"] is True
    assert result["status"] == "already_current"
    assert result["no_op"] is True
    assert result["operator_presence_required"] is False
    assert result["operator_presence_verified"] is False
    assert events == ["lock"]


@pytest.mark.parametrize("binding_changed", [False, True])
def test_noop_recheck_drift_aborts_without_verification_or_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    binding_changed: bool,
) -> None:
    prepared = _prepared(tmp_path)
    current = (
        _prepared(tmp_path, binding=_binding(tmp_path, roster_generation=31))
        if binding_changed
        else prepared
    )
    prepared_states = iter((prepared, current))
    noop_states = iter((True, bool(binding_changed)))

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        yield

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("no-op drift must not verify or mutate")

    monkeypatch.setattr(
        prepared_install,
        "_prepare",
        lambda *_args, **_kwargs: next(prepared_states),
    )
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: next(noop_states))
    monkeypatch.setattr(prepared_install, "_install_lock", lock)
    monkeypatch.setattr(prepared_install, "load_config", lambda *_args, **_kwargs: prepared.config)
    monkeypatch.setattr(prepared_install, "_verify_codex_install_operator_presence", forbidden)
    monkeypatch.setattr(prepared_install, "atomic_install_tree", forbidden)

    with pytest.raises(
        prepared_install.PreparedCodexInstallError,
        match="no-op state changed during confirmation",
    ):
        prepared_install.refresh_existing_codex_adapter(prepared.config)


def test_operator_denial_causes_zero_host_or_native_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    events: list[str] = []
    monkeypatch.setattr(prepared_install, "_prepare", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: False)

    def deny(_binding: prepared_install._CodexInstallBinding) -> None:
        events.append("verification_denied")
        raise prepared_install.PreparedCodexInstallError("operator denied")

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("denial must precede every mutation boundary")

    monkeypatch.setattr(prepared_install, "_verify_codex_install_operator_presence", deny)
    monkeypatch.setattr(prepared_install, "_install_lock", forbidden)
    monkeypatch.setattr(prepared_install, "_published_candidate", forbidden)
    monkeypatch.setattr(prepared_install, "atomic_install_tree", forbidden)
    monkeypatch.setattr(prepared_install, "_native_command", forbidden)

    with pytest.raises(prepared_install.PreparedCodexInstallError, match="operator denied"):
        prepared_install.refresh_existing_codex_adapter(prepared.config)

    assert events == ["verification_denied"]


def test_post_verification_binding_drift_refuses_before_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = _prepared(tmp_path)
    changed = _prepared(tmp_path, binding=_binding(tmp_path, roster_generation=31))
    prepared_states = iter((original, changed))
    events: list[str] = []

    def prepare(*_args: object, **_kwargs: object) -> SimpleNamespace:
        value = next(prepared_states)
        events.append(f"prepare:{value.binding.roster_generation}")
        return value

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        events.append("lock")
        yield

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("binding drift must precede target or native mutation")

    monkeypatch.setattr(prepared_install, "_prepare", prepare)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: False)
    monkeypatch.setattr(
        prepared_install,
        "_verify_codex_install_operator_presence",
        lambda _binding: events.append("verified"),
    )
    monkeypatch.setattr(prepared_install, "_install_lock", lock)
    monkeypatch.setattr(prepared_install, "load_config", lambda *_args, **_kwargs: original.config)
    monkeypatch.setattr(prepared_install, "_published_candidate", forbidden)
    monkeypatch.setattr(prepared_install, "atomic_install_tree", forbidden)
    monkeypatch.setattr(prepared_install, "_native_command", forbidden)

    with pytest.raises(
        prepared_install.PreparedCodexInstallError,
        match="state changed after operator verification",
    ):
        prepared_install.refresh_existing_codex_adapter(original.config)

    assert events == ["prepare:30", "verified", "lock", "prepare:31"]


def test_target_drift_after_publication_is_detected_before_atomic_swap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    drifted = prepared_install._ManagedTargetSnapshot(
        install_id="install-drifted",
        plugin_version=prepared.target_snapshot.plugin_version,
        bundle_sha256=_digest("d"),
        tree_sha256=_digest("e"),
        parent_device=prepared.target_snapshot.parent_device,
        parent_inode=prepared.target_snapshot.parent_inode,
    )
    events: list[str] = []
    snapshots = iter((prepared.target_snapshot, drifted))

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        yield

    def publish(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[dict[str, str], tuple[object, ...]]:
        events.append("candidate_published")
        return {"candidate": "bytes"}, ()

    def snapshot(_target: Path) -> prepared_install._ManagedTargetSnapshot:
        events.append("target_revalidated")
        return next(snapshots)

    def forbidden_swap(
        target: Path,
        _files: dict[str, str],
        **kwargs: object,
    ) -> None:
        precondition = kwargs["target_precondition"]
        assert callable(precondition)
        precondition(target)
        events.append("atomic_swap")
        raise AssertionError("target drift must be refused before the atomic swap")

    monkeypatch.setattr(prepared_install, "_prepare", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: False)
    monkeypatch.setattr(
        prepared_install,
        "_verify_codex_install_operator_presence",
        lambda _binding: None,
    )
    monkeypatch.setattr(prepared_install, "_install_lock", lock)
    monkeypatch.setattr(prepared_install, "load_config", lambda *_args, **_kwargs: prepared.config)
    monkeypatch.setattr(prepared_install, "_published_candidate", publish)
    monkeypatch.setattr(prepared_install, "revalidate_persistent_artifacts", lambda _items: None)
    monkeypatch.setattr(
        prepared_install,
        "_strict_native_state",
        lambda *_args, **_kwargs: prepared.native_state,
    )
    monkeypatch.setattr(prepared_install, "_target_snapshot", snapshot)
    monkeypatch.setattr(prepared_install, "atomic_install_tree", forbidden_swap)

    with pytest.raises(prepared_install.PreparedCodexInstallError):
        prepared_install.refresh_existing_codex_adapter(prepared.config)

    assert events == [
        "candidate_published",
        "target_revalidated",
        "target_revalidated",
    ]


def test_typed_atomic_install_failure_returns_recovery_evidence_without_native_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    backup = tmp_path / "retained-backup"
    stage = tmp_path / "retained-stage"
    failure = installer_filesystem.AtomicInstallTreeError(
        "atomic install recovery is incomplete",
        backup_path=backup,
        stage_path=stage,
        recovery_errors=("target restoration failed: injected", "stage cleanup failed: injected"),
    )

    result, events = _run_refresh_harness(
        monkeypatch,
        tmp_path,
        prepared=prepared,
        snapshots=[],
        atomic_error=failure,
    )

    assert result["ok"] is False
    assert result["status"] == "manual_recovery_required"
    assert result["backup_path"] == str(backup)
    assert result["native_steps"] == []
    assert result["partial"] is True
    assert result["compensation"] == {
        "compensated": False,
        "manual_recovery_required": True,
        "backup_verified": True,
        "stage_path": str(stage),
        "recovery_errors": [
            "target restoration failed: injected",
            "stage cleanup failed: injected",
        ],
        "error": "atomic install recovery is incomplete",
    }
    assert not any(isinstance(event, tuple) and event[0] == "native_command" for event in events)


def test_native_refresh_orders_remove_before_add_and_proves_final_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    absent = prepared_install._CodexNativeState(
        False,
        None,
        "",
        _digest("b"),
        prepared.native_state.marketplace_state_sha256,
    )
    final = prepared_install._CodexNativeState(
        True,
        True,
        prepared.binding.candidate_plugin_version,
        _digest("c"),
        prepared.native_state.marketplace_state_sha256,
    )
    installed = _installed_snapshot(prepared)
    native_states = iter((prepared.native_state, absent, final))
    events: list[object] = []

    def forbidden_canary_mutation(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("prepared refresh must preserve canary Store evidence")

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        events.append("lock")
        yield

    def strict_state(*_args: object, **_kwargs: object) -> prepared_install._CodexNativeState:
        state = next(native_states)
        events.append(("native_state", state.plugin_version, state.plugin_present))
        return state

    def native_command(
        _prepared: SimpleNamespace,
        arguments: list[str],
        *,
        name: str,
        steps: list[dict[str, Any]],
        timeout: float = 30,
    ) -> NativeCommandResult:
        del _prepared, timeout
        events.append((name, tuple(arguments)))
        result = _successful_native_result(tuple(arguments))
        steps.append({"name": name, **result.to_dict()})
        return result

    def install_tree(*_args: object, **_kwargs: object) -> dict[str, Any]:
        events.append("target_swap")
        return {
            "backup_path": str(tmp_path / "backup"),
            "bundle_digest": installed.bundle_sha256,
            "changed": True,
        }

    monkeypatch.setattr(prepared_install, "_prepare", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: False)
    monkeypatch.setattr(
        prepared_install,
        "_verify_codex_install_operator_presence",
        lambda _binding: events.append("verified"),
    )
    monkeypatch.setattr(prepared_install, "_install_lock", lock)
    monkeypatch.setattr(prepared_install, "load_config", lambda *_args, **_kwargs: prepared.config)
    monkeypatch.setattr(
        prepared_install,
        "_published_candidate",
        lambda *_args, **_kwargs: ({"candidate": "bytes"}, ()),
    )
    monkeypatch.setattr(prepared_install, "revalidate_persistent_artifacts", lambda _items: None)
    monkeypatch.setattr(prepared_install, "_strict_native_state", strict_state)
    monkeypatch.setattr(prepared_install, "_require_frozen_target", lambda *_args: None)
    monkeypatch.setattr(prepared_install, "_target_snapshot", lambda _target: installed)
    monkeypatch.setattr(prepared_install, "atomic_install_tree", install_tree)
    monkeypatch.setattr(
        prepared_install,
        "_managed_bundle_identity",
        lambda *_args, **_kwargs: (
            prepared.binding.candidate_plugin_version,
            "installed-id",
            "installed-bundle",
        ),
    )
    monkeypatch.setattr(prepared_install, "_native_command", native_command)
    monkeypatch.setattr(
        installer_inventory,
        "_invalidate_canary_attestation",
        forbidden_canary_mutation,
    )
    assert not hasattr(prepared_install, "_invalidate_canary_attestation")

    result = prepared_install.refresh_existing_codex_adapter(prepared.config)

    remove_index = events.index(
        (
            "plugin_remove_for_refresh",
            ("plugin", "remove", prepared_install._SELECTOR, "--json"),
        )
    )
    add_index = events.index(
        ("plugin_add", ("plugin", "add", prepared_install._SELECTOR, "--json"))
    )
    assert events.index("target_swap") < remove_index < add_index
    assert result["ok"] is True
    assert result["complete"] is True
    assert result["status"] == "registered"
    assert result["registered"] is True
    assert result["enabled"] is True
    assert result["candidate_plugin_version"] == final.plugin_version
    assert result["candidate_plan_sha256"] == prepared.binding.candidate_plan_sha256
    assert result["published_bundle_sha256"] == installed.bundle_sha256
    assert result["canary"] is None
    assert result["canary_attestation_invalidated"] is False
    assert result["hook_trust_status"] == "unverified"
    assert result["transaction_complete"] is True
    assert result["activation_complete"] is False
    assert result["activation_required"] is True
    assert result["loaded"] is None
    assert result["restart_required"] is True


def test_unproven_post_swap_identity_retains_backup_for_manual_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    backup = tmp_path / "exact-backup"

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        yield

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "unproven operation-created state must not authorize native mutation or restore"
        )

    monkeypatch.setattr(prepared_install, "_prepare", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: False)
    monkeypatch.setattr(
        prepared_install,
        "_verify_codex_install_operator_presence",
        lambda _binding: None,
    )
    monkeypatch.setattr(prepared_install, "_install_lock", lock)
    monkeypatch.setattr(prepared_install, "load_config", lambda *_args, **_kwargs: prepared.config)
    monkeypatch.setattr(
        prepared_install,
        "_published_candidate",
        lambda *_args, **_kwargs: ({"candidate": "bytes"}, ()),
    )
    monkeypatch.setattr(prepared_install, "revalidate_persistent_artifacts", lambda _items: None)
    monkeypatch.setattr(
        prepared_install,
        "_strict_native_state",
        lambda *_args, **_kwargs: prepared.native_state,
    )
    monkeypatch.setattr(prepared_install, "_require_frozen_target", lambda *_args: None)
    monkeypatch.setattr(
        prepared_install,
        "atomic_install_tree",
        lambda *_args, **_kwargs: {
            "backup_path": str(backup),
            "bundle_digest": _digest("f"),
            "changed": True,
        },
    )

    def unproven_target(_target: Path) -> prepared_install._ManagedTargetSnapshot:
        raise prepared_install.PreparedCodexInstallError("unproven target")

    monkeypatch.setattr(prepared_install, "_target_snapshot", unproven_target)
    monkeypatch.setattr(prepared_install, "_native_command", forbidden)
    monkeypatch.setattr(prepared_install, "_compensate", forbidden)

    result = prepared_install.refresh_existing_codex_adapter(prepared.config)

    assert result["ok"] is False
    assert result["complete"] is False
    assert result["status"] == "manual_recovery_required"
    assert result["backup_path"] == str(backup)
    assert result["partial"] is True
    assert result["native_steps"] == []
    assert result["compensation"] == {
        "compensated": False,
        "manual_recovery_required": True,
        "error": (
            "the published target identity is unproven; retained the exact backup "
            "instead of overwriting ambiguous state"
        ),
    }


@pytest.mark.parametrize(
    ("plugin_version", "bundle_sha256"),
    [
        ("9.9.9", _digest("f")),
        ("0.2.0", _digest("e")),
    ],
)
def test_wrong_post_swap_version_or_bundle_is_not_authorized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    plugin_version: str,
    bundle_sha256: str,
) -> None:
    prepared = _prepared(tmp_path)
    observed = _installed_snapshot(
        prepared,
        plugin_version=plugin_version,
        bundle_sha256=bundle_sha256,
    )

    result, events = _run_refresh_harness(
        monkeypatch,
        tmp_path,
        prepared=prepared,
        snapshots=[observed],
    )

    assert result["ok"] is False
    assert result["status"] == "manual_recovery_required"
    assert "does not match the authorized candidate" in result["error"]
    assert not any(isinstance(event, tuple) and event[0] == "native_command" for event in events)
    assert "compensation" not in events


def test_successful_add_command_without_matching_inventory_is_not_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    absent = prepared_install._CodexNativeState(
        False,
        None,
        "",
        _digest("b"),
        prepared.native_state.marketplace_state_sha256,
    )
    wrong_final = prepared_install._CodexNativeState(
        True,
        True,
        prepared.binding.current_plugin_version,
        prepared.native_state.plugin_state_sha256,
        prepared.native_state.marketplace_state_sha256,
    )
    installed = _installed_snapshot(prepared)
    native_states = iter((prepared.native_state, absent, wrong_final))

    def forbidden_canary_mutation(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("failed refresh must preserve canary Store evidence")

    @contextmanager
    def lock(*, home_dir: str | Path | None):
        del home_dir
        yield

    monkeypatch.setattr(prepared_install, "_prepare", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(prepared_install, "_is_noop", lambda _prepared: False)
    monkeypatch.setattr(
        prepared_install,
        "_verify_codex_install_operator_presence",
        lambda _binding: None,
    )
    monkeypatch.setattr(prepared_install, "_install_lock", lock)
    monkeypatch.setattr(prepared_install, "load_config", lambda *_args, **_kwargs: prepared.config)
    monkeypatch.setattr(
        prepared_install,
        "_published_candidate",
        lambda *_args, **_kwargs: ({"candidate": "bytes"}, ()),
    )
    monkeypatch.setattr(prepared_install, "revalidate_persistent_artifacts", lambda _items: None)
    monkeypatch.setattr(
        prepared_install,
        "_strict_native_state",
        lambda *_args, **_kwargs: next(native_states),
    )
    monkeypatch.setattr(prepared_install, "_require_frozen_target", lambda *_args: None)
    monkeypatch.setattr(prepared_install, "_target_snapshot", lambda _target: installed)
    monkeypatch.setattr(
        prepared_install,
        "atomic_install_tree",
        lambda *_args, **_kwargs: {
            "backup_path": str(tmp_path / "backup"),
            "bundle_digest": installed.bundle_sha256,
        },
    )
    monkeypatch.setattr(
        prepared_install,
        "_native_command",
        lambda _prepared, arguments, **_kwargs: _successful_native_result(tuple(arguments)),
    )
    monkeypatch.setattr(
        prepared_install,
        "_compensate",
        lambda *_args, **_kwargs: {
            "compensated": False,
            "manual_recovery_required": True,
            "error": "postcondition mismatch",
        },
    )
    monkeypatch.setattr(
        installer_inventory,
        "_invalidate_canary_attestation",
        forbidden_canary_mutation,
    )
    assert not hasattr(prepared_install, "_invalidate_canary_attestation")

    result = prepared_install.refresh_existing_codex_adapter(prepared.config)

    assert result["ok"] is False
    assert result["complete"] is False
    assert result["status"] == "manual_recovery_required"
    assert "postcondition" in result["error"]


def test_final_target_drift_prevents_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)
    drifted = _installed_snapshot(prepared, tree_sha256=_digest("e"))

    result, events = _run_refresh_harness(
        monkeypatch,
        tmp_path,
        prepared=prepared,
        snapshots=[installed, drifted],
    )

    assert result["ok"] is False
    assert result["status"] == "manual_recovery_required"
    assert "candidate changed before success" in result["error"]
    assert ("native_command", "plugin_remove_for_refresh") in events
    assert ("native_command", "plugin_add") in events
    assert ("launcher_revalidate", 2) not in events
    assert "compensation" in events


def test_final_launcher_drift_prevents_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)

    result, events = _run_refresh_harness(
        monkeypatch,
        tmp_path,
        prepared=prepared,
        snapshots=[installed, installed],
        fail_launcher_revalidation_at=2,
    )

    assert result["ok"] is False
    assert result["status"] == "manual_recovery_required"
    assert "launcher identity drift" in result["error"]
    assert ("launcher_revalidate", 2) in events
    assert "compensation" in events


def test_compensation_removes_candidate_restores_target_then_readds_prior_plugin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)
    candidate = prepared_install._CodexNativeState(
        True,
        True,
        prepared.binding.candidate_plugin_version,
        _digest("c"),
        prepared.native_state.marketplace_state_sha256,
    )
    absent = prepared_install._CodexNativeState(
        False,
        None,
        "",
        _digest("b"),
        prepared.native_state.marketplace_state_sha256,
    )
    states = iter((candidate, absent, prepared.native_state))
    events: list[object] = []

    def native_command(
        _prepared: SimpleNamespace,
        arguments: list[str],
        *,
        name: str,
        steps: list[dict[str, Any]],
        timeout: float = 30,
    ) -> NativeCommandResult:
        del _prepared, steps, timeout
        events.append((name, tuple(arguments)))
        return _successful_native_result(tuple(arguments))

    monkeypatch.setattr(
        prepared_install,
        "_native_state_or_none",
        lambda *_args, **_kwargs: next(states),
    )
    monkeypatch.setattr(prepared_install, "_native_command", native_command)
    monkeypatch.setattr(prepared_install, "_frozen_backup_error", lambda *_args: None)
    monkeypatch.setattr(prepared_install, "_target_snapshot", lambda _target: installed)
    monkeypatch.setattr(prepared_install, "_require_frozen_target", lambda *_args: None)

    def restore(*_args: object, **_kwargs: object) -> tuple[bool, str, None]:
        events.append("target_restored")
        return True, str(tmp_path / "displaced"), None

    monkeypatch.setattr(prepared_install, "_conditional_restore_target", restore)

    result = prepared_install._compensate(
        prepared,
        home_dir=None,
        backup_path=tmp_path / "backup",
        installed_snapshot=installed,
        steps=[],
    )

    assert events == [
        (
            "compensation_remove_candidate",
            ("plugin", "remove", prepared_install._SELECTOR, "--json"),
        ),
        "target_restored",
        (
            "compensation_restore_plugin",
            ("plugin", "add", prepared_install._SELECTOR, "--json"),
        ),
    ]
    assert result["compensated"] is True
    assert result["manual_recovery_required"] is False


def test_final_prior_target_drift_prevents_full_compensation_claim(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)
    candidate = prepared_install._CodexNativeState(
        True,
        True,
        prepared.binding.candidate_plugin_version,
        _digest("c"),
        prepared.native_state.marketplace_state_sha256,
    )
    absent = prepared_install._CodexNativeState(
        False,
        None,
        "",
        _digest("b"),
        prepared.native_state.marketplace_state_sha256,
    )
    states = iter((candidate, absent, prepared.native_state))
    events: list[str] = []

    def native_command(
        _prepared: SimpleNamespace,
        _arguments: list[str],
        *,
        name: str,
        steps: list[dict[str, Any]],
        timeout: float = 30,
    ) -> NativeCommandResult:
        del _prepared, steps, timeout
        events.append(name)
        return _successful_native_result((name,))

    monkeypatch.setattr(
        prepared_install,
        "_native_state_or_none",
        lambda *_args, **_kwargs: next(states),
    )
    monkeypatch.setattr(prepared_install, "_native_command", native_command)
    monkeypatch.setattr(prepared_install, "_frozen_backup_error", lambda *_args: None)
    monkeypatch.setattr(prepared_install, "_target_snapshot", lambda _target: installed)
    monkeypatch.setattr(
        prepared_install,
        "_conditional_restore_target",
        lambda *_args, **_kwargs: (True, str(tmp_path / "displaced"), None),
    )

    def drifted_prior(*_args: object) -> None:
        events.append("final_target_check")
        raise prepared_install.PreparedCodexInstallError("target drift")

    monkeypatch.setattr(prepared_install, "_require_frozen_target", drifted_prior)

    result = prepared_install._compensate(
        prepared,
        home_dir=tmp_path,
        backup_path=tmp_path / "backup",
        installed_snapshot=installed,
        steps=[],
    )

    assert events == [
        "compensation_remove_candidate",
        "compensation_restore_plugin",
        "final_target_check",
    ]
    assert result["compensated"] is False
    assert result["manual_recovery_required"] is True
    assert result["displaced_path"] == str(tmp_path / "displaced")
    assert result["error"] == "prior Codex target changed before compensation completed"


def test_tampered_backup_tree_blocks_compensation_before_live_target_move(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)
    backup = tmp_path / "backup"
    tampered_backup = prepared_install._ManagedTargetSnapshot(
        install_id=prepared.target_snapshot.install_id,
        plugin_version=prepared.target_snapshot.plugin_version,
        bundle_sha256=prepared.target_snapshot.bundle_sha256,
        tree_sha256=_digest("e"),
        parent_device=prepared.target_snapshot.parent_device,
        parent_inode=prepared.target_snapshot.parent_inode,
    )
    replace_calls: list[tuple[Path, Path]] = []

    def snapshot(path: Path) -> prepared_install._ManagedTargetSnapshot:
        return tampered_backup if Path(path) == backup else installed

    def replace(source: Path, destination: Path) -> None:
        replace_calls.append((Path(source), Path(destination)))

    monkeypatch.setattr(prepared_install, "_target_snapshot", snapshot)
    monkeypatch.setattr(
        prepared_install,
        "ensure_private_directory",
        lambda path, **_kwargs: Path(path),
    )
    monkeypatch.setattr(prepared_install.os, "replace", replace)

    restored, displaced, error = prepared_install._conditional_restore_target(
        prepared,
        home_dir=tmp_path,
        backup_path=backup,
        installed_snapshot=installed,
    )

    assert restored is False
    assert displaced is None
    assert error is not None
    assert "backup" in error.lower()
    assert replace_calls == []


def test_tampered_backup_stops_before_candidate_plugin_removal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)
    candidate = prepared_install._CodexNativeState(
        True,
        True,
        prepared.binding.candidate_plugin_version,
        _digest("c"),
        prepared.native_state.marketplace_state_sha256,
    )

    monkeypatch.setattr(
        prepared_install,
        "_native_state_or_none",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        prepared_install,
        "_frozen_backup_error",
        lambda *_args: "exact Codex backup changed after target publication",
    )
    monkeypatch.setattr(prepared_install, "_target_snapshot", lambda _target: installed)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("tampered backup must not authorize native or live-target mutation")

    monkeypatch.setattr(prepared_install, "_native_command", forbidden)
    monkeypatch.setattr(prepared_install, "_conditional_restore_target", forbidden)

    result = prepared_install._compensate(
        prepared,
        home_dir=tmp_path,
        backup_path=tmp_path / "backup",
        installed_snapshot=installed,
        steps=[],
    )

    assert result == {
        "compensated": False,
        "manual_recovery_required": True,
        "error": "exact Codex backup changed after target publication",
    }


def test_candidate_tamper_stops_before_native_compensation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)
    tampered = _installed_snapshot(prepared, tree_sha256=_digest("e"))
    candidate = prepared_install._CodexNativeState(
        True,
        True,
        prepared.binding.candidate_plugin_version,
        _digest("c"),
        prepared.native_state.marketplace_state_sha256,
    )
    monkeypatch.setattr(
        prepared_install,
        "_native_state_or_none",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(prepared_install, "_target_snapshot", lambda _target: tampered)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("candidate drift must precede compensation mutation")

    monkeypatch.setattr(prepared_install, "_native_command", forbidden)
    monkeypatch.setattr(prepared_install, "_frozen_backup_error", forbidden)
    monkeypatch.setattr(prepared_install, "_conditional_restore_target", forbidden)

    result = prepared_install._compensate(
        prepared,
        home_dir=tmp_path,
        backup_path=tmp_path / "backup",
        installed_snapshot=installed,
        steps=[],
    )

    assert result == {
        "compensated": False,
        "manual_recovery_required": True,
        "error": "published Codex candidate changed before compensation",
    }


def test_failed_post_restore_verification_reverses_to_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    backup = tmp_path / "backup"
    recovery_root = tmp_path / "recovery"
    recovery_root.mkdir()
    displaced = recovery_root / "failed-refresh-123"
    locations: dict[Path, str] = {
        prepared.target: "candidate",
        backup: "prior",
    }
    replacements: list[tuple[Path, Path]] = []
    candidate_snapshot = prepared_install._ManagedTargetSnapshot(
        install_id="installed-id",
        plugin_version=prepared.binding.candidate_plugin_version,
        bundle_sha256="installed-bundle",
        tree_sha256=_digest("f"),
        parent_device=prepared.target_snapshot.parent_device,
        parent_inode=prepared.target_snapshot.parent_inode,
    )
    bad_prior_snapshot = prepared_install._ManagedTargetSnapshot(
        install_id=prepared.target_snapshot.install_id,
        plugin_version=prepared.target_snapshot.plugin_version,
        bundle_sha256=prepared.target_snapshot.bundle_sha256,
        tree_sha256=_digest("e"),
        parent_device=prepared.target_snapshot.parent_device,
        parent_inode=prepared.target_snapshot.parent_inode,
    )

    def snapshot(path: Path) -> prepared_install._ManagedTargetSnapshot:
        key = Path(path)
        kind = locations[key]
        if kind == "candidate":
            return candidate_snapshot
        if key == backup:
            return prepared.target_snapshot
        return bad_prior_snapshot

    def replace(source: Path, destination: Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        replacements.append((source_path, destination_path))
        kind = locations.pop(source_path)
        locations.pop(destination_path, None)
        locations[destination_path] = kind

    monkeypatch.setattr(prepared_install, "_target_snapshot", snapshot)
    monkeypatch.setattr(
        prepared_install,
        "ensure_private_directory",
        lambda _path, **_kwargs: recovery_root,
    )
    monkeypatch.setattr(prepared_install.time, "time_ns", lambda: 123)
    monkeypatch.setattr(prepared_install.os, "replace", replace)

    restored, reported_displaced, error = prepared_install._conditional_restore_target(
        prepared,
        home_dir=tmp_path,
        backup_path=backup,
        installed_snapshot=candidate_snapshot,
    )

    assert restored is False
    assert error is not None
    assert locations[prepared.target] == "candidate"
    assert sum(kind == "prior" for kind in locations.values()) == 1
    assert replacements[:2] == [
        (prepared.target, displaced),
        (backup, prepared.target),
    ]
    assert replacements[-1] == (displaced, prepared.target)
    assert reported_displaced is None or Path(reported_displaced) != displaced


def test_compensation_stops_on_conflicting_native_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = _prepared(tmp_path)
    installed = _installed_snapshot(prepared)
    conflict = prepared_install._CodexNativeState(
        True,
        False,
        "9.9.9",
        _digest("d"),
        prepared.native_state.marketplace_state_sha256,
    )
    monkeypatch.setattr(
        prepared_install,
        "_native_state_or_none",
        lambda *_args, **_kwargs: conflict,
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("ambiguous native state must not authorize compensation")

    monkeypatch.setattr(prepared_install, "_conditional_restore_target", forbidden)
    monkeypatch.setattr(prepared_install, "_native_command", forbidden)
    monkeypatch.setattr(prepared_install, "_frozen_backup_error", lambda *_args: None)
    monkeypatch.setattr(prepared_install, "_target_snapshot", lambda _target: installed)

    result = prepared_install._compensate(
        prepared,
        home_dir=None,
        backup_path=tmp_path / "backup",
        installed_snapshot=installed,
        steps=[],
    )

    assert result["compensated"] is False
    assert result["manual_recovery_required"] is True
    assert "conflicts" in result["error"]
