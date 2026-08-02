"""Focused ownership, prepared-authority, and postcondition tests for uninstall."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import installer_uninstall as uninstall_subject
from agency_runtime.core import prepared_host_uninstall as prepared
from agency_runtime.core.codex_global_guidance import install_codex_global_guidance
from agency_runtime.core.installer import (
    INSTALL_MANIFEST,
    _host_root,
    _validate_owned_install_tree,
    install_agent_adapter,
    plan_agent_uninstall,
)
from agency_runtime.core.installer_contracts import MARKETPLACE_ID, PLUGIN_ID
from agency_runtime.core.installer_uninstall import _commit_agent_uninstall
from agency_runtime.core.installer_zcode import zcode_config_path
from agency_runtime.core.prepared_host_uninstall import (
    PreparedHostUninstallError,
    _apply_prepared_host_uninstall,
    uninstall_plan_digest,
)
from agency_runtime.core.private_paths import ensure_private_directory


def _resolver(*present: str):
    selected = set(present)
    return lambda name: str(Path("C:/fake") / f"{name}.exe") if name in selected else None


def _tree_snapshot(root: Path) -> dict[str, bytes | None]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def test_recovery_command_quotes_shell_metacharacters() -> None:
    retained = (
        r"C:\Users\operator&reviewer\Agency Backup"
        if os.name == "nt"
        else "/tmp/operator&reviewer/Agency Backup"
    )

    command = uninstall_subject._recovery_command("codex", retained)

    assert retained in command
    if os.name == "nt":
        assert command.startswith("& 'agency' 'install'")
        assert command.endswith(f"'{retained}'")
    else:
        assert command.endswith("'/tmp/operator&reviewer/Agency Backup'")


def _stage_owned_bundle(host: str, home: Path) -> dict[str, Any]:
    (home / ".agency-runtime").mkdir(parents=True, exist_ok=True)
    root = _host_root(host, home_dir=home)
    root.mkdir(parents=True, exist_ok=True)
    if host == "zcode":
        config = zcode_config_path(home_dir=home)
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps(
                {
                    "theme": "keep-me",
                    "hooks": {
                        "enabled": False,
                        "events": {"UnrelatedEvent": [{"name": "keep-me"}]},
                    },
                }
            ),
            encoding="utf-8",
        )
    result = install_agent_adapter(host, home_dir=home)
    assert result["ok"] is True, (
        result.get("status"),
        result.get("failed_step"),
        result.get("error"),
        result.get("native_steps"),
    )
    assert Path(result["target"], INSTALL_MANIFEST).is_file()
    return result


class UninstallNativeRunner:
    """Stateful model of native inventories, provenance, and unregister calls."""

    def __init__(
        self,
        host: str,
        target: Path,
        *,
        present: bool = True,
        plugin_record_count: int = 1,
        plugin_binding: str = "exact",
        marketplace_present: bool | None = None,
        marketplace_record_count: int = 1,
        marketplace_binding: str = "exact",
        gateway_live: bool = False,
        sticky_plugin: bool = False,
        fail_mutation_secret: str | None = None,
        remove_marketplace_on_uninstall: bool = False,
    ) -> None:
        self.host = host
        self.target = target.resolve()
        self.present = present
        self.enabled = present
        self.plugin_record_count = plugin_record_count
        self.plugin_binding = plugin_binding
        self.marketplace_present = (
            present and host in {"codex", "claude"}
            if marketplace_present is None
            else marketplace_present
        )
        self.marketplace_record_count = marketplace_record_count
        self.marketplace_binding = marketplace_binding
        self.gateway_live = gateway_live
        self.sticky_plugin = sticky_plugin
        self.fail_mutation_secret = fail_mutation_secret
        self.remove_marketplace_on_uninstall = remove_marketplace_on_uninstall
        self.binding_revision = "stable"
        self.commands: list[list[str]] = []
        self.mutation_commands: list[list[str]] = []
        self.marketplace_list_count = 0
        self.openclaw_inspect_count = 0

    def _bound_path(self) -> str:
        return str(
            self.target
            if self.plugin_binding == "exact"
            else self.target.parent / "not-the-agency-target"
        )

    def _plugin_record(self, *, inspected: bool = False) -> dict[str, Any]:
        identity = "id" if self.host == "openclaw" else "pluginId"
        record: dict[str, Any] = {
            identity: PLUGIN_ID,
            "enabled": True,
            "revision": self.binding_revision,
        }
        if self.host == "openclaw" and inspected:
            record["source"] = {"path": self._bound_path()}
        elif self.host in {"codex", "claude"}:
            record.update(
                {
                    "marketplaceName": MARKETPLACE_ID,
                    "path": str(Path(self._bound_path()) / "plugins" / PLUGIN_ID),
                    "source": "local",
                }
            )
            if self.plugin_binding == "ambiguous":
                record["root"] = str(self.target.parent / "conflicting-plugin-root")
            elif self.plugin_binding == "relative":
                record["source"] = "../conflicting-plugin-root"
        return record

    def _plugin_inventory(self, *, inspected: bool = False) -> dict[str, Any]:
        if not self.present:
            return {"returncode": 0, "stdout": json.dumps([])}
        if self.host == "hermes":
            state = "enabled" if self.enabled else "disabled"
            rows = [f"{PLUGIN_ID} {state}" for _ in range(self.plugin_record_count)]
            return {"returncode": 0, "stdout": "\n".join(rows) + "\n"}
        records = [
            self._plugin_record(inspected=inspected) for _ in range(self.plugin_record_count)
        ]
        if inspected and self.host == "openclaw" and len(records) == 1:
            payload: Any = records[0]
        else:
            payload = {"plugins": records} if self.host == "openclaw" else records
        return {"returncode": 0, "stdout": json.dumps(payload)}

    def _marketplace_inventory(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        if self.marketplace_present:
            for _ in range(self.marketplace_record_count):
                record: dict[str, Any] = {
                    "name": MARKETPLACE_ID,
                    "revision": self.binding_revision,
                }
                if self.marketplace_binding == "exact":
                    record["source"] = str(self.target)
                elif self.marketplace_binding == "wrong":
                    record["source"] = str(self.target.parent / "wrong-marketplace")
                elif self.marketplace_binding == "ambiguous":
                    record["source"] = str(self.target)
                    record["root"] = str(self.target.parent / "wrong-marketplace")
                elif self.marketplace_binding == "relative":
                    record["source"] = str(self.target)
                    record["path"] = "../wrong-marketplace"
                records.append(record)
        records.append({"name": "unrelated-marketplace", "source": "C:/unrelated"})
        return {"returncode": 0, "stdout": json.dumps(records)}

    def __call__(self, command: list[str], **_kwargs: Any) -> dict[str, Any]:
        command = list(command)
        self.commands.append(command)
        if command[1:] == ["--version"]:
            version = "OpenClaw 2026.7.1" if self.host == "openclaw" else f"{self.host} 1.0"
            return {"returncode": 0, "stdout": version}
        if command[1:4] == ["gateway", "status", "--deep"]:
            return {"returncode": 0, "stdout": json.dumps({"running": self.gateway_live})}
        if command[1:5] == ["plugin", "marketplace", "list", "--json"]:
            self.marketplace_list_count += 1
            return self._marketplace_inventory()
        if command[1:4] == ["plugin", "marketplace", "remove"]:
            raise AssertionError("uninstall must preserve native marketplace registration")
        if command[1:4] == ["plugins", "inspect", PLUGIN_ID]:
            self.openclaw_inspect_count += 1
            return self._plugin_inventory(inspected=True)
        if (
            command[1:3] == ["plugins", "disable"]
            or command[1:3] == ["plugins", "uninstall"]
            or command[1:3] == ["plugin", "remove"]
            or command[1:3] == ["plugin", "uninstall"]
        ):
            self.mutation_commands.append(command)
            if self.host == "openclaw":
                assert command[-2:] == ["--keep-files", "--force"]
            if self.fail_mutation_secret is not None:
                return {
                    "returncode": 9,
                    "stderr": f"native detail must stay private: {self.fail_mutation_secret}",
                }
            if not self.sticky_plugin:
                if self.host == "hermes":
                    self.enabled = False
                else:
                    self.present = False
            if self.remove_marketplace_on_uninstall:
                self.marketplace_present = False
            return {"returncode": 0, "stdout": "{}"}
        if tuple(command[1:3]) in {("plugin", "list"), ("plugins", "list")}:
            return self._plugin_inventory()
        raise AssertionError(f"unexpected {self.host} command: {command!r}")


class MultiHostRunner:
    def __init__(self, *runners: UninstallNativeRunner) -> None:
        self.runners = {runner.host: runner for runner in runners}

    def __call__(self, command: list[str], **kwargs: Any) -> dict[str, Any]:
        executable = Path(command[0]).stem.casefold()
        for host, runner in self.runners.items():
            if executable == host:
                return runner(command, **kwargs)
        raise AssertionError(f"unexpected executable: {command[0]!r}")


def _plan(
    host: str,
    home: Path,
    runner: UninstallNativeRunner | MultiHostRunner,
    *,
    resolver_hosts: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    return plan_agent_uninstall(
        host,
        home_dir=home,
        binary_resolver=_resolver(*(resolver_hosts or (host,))),
        command_runner=runner,
    )


def _digest(plans: list[dict[str, Any]], *, selected_by: str = "agent") -> str:
    targets = [str(plan["host"]) for plan in plans]
    return uninstall_plan_digest(plans, selected_by=selected_by, targets=targets)


def _operation_id(label: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"agency-runtime-test:{label}"))


def test_owned_install_tree_validation_is_exact(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])

    valid, error, manifest = _validate_owned_install_tree(
        target,
        host="codex",
        target=target,
    )

    assert valid is True
    assert error is None
    assert manifest is not None
    assert manifest["install_id"] == str(uuid.UUID(manifest["install_id"]))

    (target / "not-owned-by-agency.txt").write_text(
        "user data must never be moved\n",
        encoding="utf-8",
    )
    valid, error, manifest = _validate_owned_install_tree(
        target,
        host="codex",
        target=target,
    )

    assert valid is False
    assert error == "Install tree contains missing or unexpected entries"
    assert manifest is None


def test_owned_install_tree_rejects_missing_file_and_noncanonical_install_id(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    manifest_path = target / INSTALL_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (target / manifest["owned_files"][0]).unlink()

    valid, error, _manifest = _validate_owned_install_tree(
        target,
        host="codex",
        target=target,
    )
    assert valid is False
    assert error == "Install tree contains missing or unexpected entries"

    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    manifest_path = target / INSTALL_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["install_id"] = manifest["install_id"].upper()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    valid, error, _manifest = _validate_owned_install_tree(
        target,
        host="codex",
        target=target,
    )
    assert valid is False
    assert error == "Install ownership manifest has a noncanonical install_id"


@pytest.mark.parametrize(
    ("host", "transition"),
    [
        ("hermes", "disable+retain"),
        ("openclaw", "unregister+retain"),
        ("codex", "unregister+retain"),
        ("claude", "unregister+retain"),
        ("zcode", "remove-handlers+retain"),
    ],
)
def test_prepared_uninstall_uses_canonical_transition_and_deterministic_retention(
    host: str,
    transition: str,
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle(host, tmp_path)
    target = Path(installed["target"])
    codex_agents: Path | None = None
    if host == "codex":
        codex_agents = tmp_path / ".codex" / "AGENTS.md"
        codex_agents.write_text("# Owner guidance\n", encoding="utf-8")
        install_codex_global_guidance(tmp_path / ".codex")
    runner = UninstallNativeRunner(host, target)
    before = _tree_snapshot(tmp_path)

    plan = _plan(host, tmp_path, runner)

    assert plan["ok"] is True, plan.get("error")
    assert plan["status"] == "planned"
    assert plan["would_change"] is True
    assert runner.mutation_commands == []
    assert _tree_snapshot(tmp_path) == before

    bindings: list[Any] = []
    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", bindings.append)
    operation_id = _operation_id(host)
    results = _apply_prepared_host_uninstall(
        [host],
        expected_plan_digest=_digest([plan]),
        operation_id=operation_id,
        selected_by="agent",
        home_dir=tmp_path,
        binary_resolver=_resolver(host),
        command_runner=runner,
    )

    assert len(bindings) == 1
    assert bindings[0].targets_csv == host
    assert bindings[0].transitions_csv == f"{host}:{transition}"
    assert len(results) == 1
    result = results[0]
    assert result["ok"] is True, (
        result.get("status"),
        result.get("failed_step"),
        result.get("error"),
        result.get("native_steps"),
    )
    assert result["complete"] is True
    assert result["status"] == "uninstalled"
    assert result["marketplace_registration_removed"] is False
    assert result["agency_configuration_removed"] is False
    retained = (
        tmp_path / ".agency-runtime" / "backups" / host / f"uninstall-{operation_id}"
    ).resolve()
    assert result["retained_path"] == str(retained)
    assert result["recovery_backup"] == str(retained)
    assert "--backup" in result["recovery"]
    assert str(retained) in result["recovery"]
    assert target.exists() is False
    assert (retained / INSTALL_MANIFEST).is_file()
    if codex_agents is not None:
        assert result["global_guidance"]["status"] == "removed"
        assert codex_agents.read_text(encoding="utf-8") == "# Owner guidance\n"
    if host == "openclaw":
        assert runner.openclaw_inspect_count >= 3
        assert any(command[-1] == "--force" for command in runner.mutation_commands)
    if host in {"codex", "claude"}:
        assert runner.marketplace_present is True
        assert runner.marketplace_list_count >= 5
    if host == "zcode":
        config = json.loads(zcode_config_path(home_dir=tmp_path).read_text(encoding="utf-8"))
        assert config["theme"] == "keep-me"
        assert config["hooks"]["enabled"] is False
        assert config["hooks"]["events"] == {"UnrelatedEvent": [{"name": "keep-me"}]}
    else:
        assert len(runner.mutation_commands) == 1


def test_prepared_uninstall_uses_retain_only_when_native_registration_is_absent(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("codex", target, present=False)
    plan = _plan("codex", tmp_path, runner)
    bindings: list[Any] = []
    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", bindings.append)

    result = _apply_prepared_host_uninstall(
        ["codex"],
        expected_plan_digest=_digest([plan]),
        operation_id=_operation_id("retain-only"),
        selected_by="agent",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )[0]

    assert bindings[0].transitions_csv == "codex:retain-only"
    assert result["ok"] is True
    assert runner.mutation_commands == []


def test_prepared_verifier_denial_causes_zero_host_mutation(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("codex", target)
    plan = _plan("codex", tmp_path, runner)

    def deny(_binding: object) -> None:
        raise PreparedHostUninstallError("operator denied prepared uninstall")

    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", deny)

    with pytest.raises(PreparedHostUninstallError, match="operator denied"):
        _apply_prepared_host_uninstall(
            ["codex"],
            expected_plan_digest=_digest([plan]),
            operation_id=_operation_id("denied"),
            selected_by="agent",
            home_dir=tmp_path,
            binary_resolver=_resolver("codex"),
            command_runner=runner,
        )

    assert runner.mutation_commands == []
    assert target.is_dir()


def test_prepared_uninstall_rejects_stale_plan_before_verification(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("codex", target)
    plan = _plan("codex", tmp_path, runner)
    verified: list[object] = []
    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", verified.append)
    runner.binding_revision = "changed-before-apply"

    with pytest.raises(PreparedHostUninstallError, match="changed before operator verification"):
        _apply_prepared_host_uninstall(
            ["codex"],
            expected_plan_digest=_digest([plan]),
            operation_id=_operation_id("stale-plan"),
            selected_by="agent",
            home_dir=tmp_path,
            binary_resolver=_resolver("codex"),
            command_runner=runner,
        )

    assert verified == []
    assert runner.mutation_commands == []
    assert target.is_dir()


def test_prepared_uninstall_rejects_binding_change_after_verification(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("openclaw", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("openclaw", target)
    plan = _plan("openclaw", tmp_path, runner)

    def change_binding(_binding: object) -> None:
        runner.binding_revision = "changed-after-verification"

    monkeypatch.setattr(
        prepared,
        "_require_host_uninstall_authority",
        change_binding,
    )

    with pytest.raises(
        PreparedHostUninstallError, match="plan changed after operator verification"
    ):
        _apply_prepared_host_uninstall(
            ["openclaw"],
            expected_plan_digest=_digest([plan]),
            operation_id=_operation_id("stale-binding"),
            selected_by="agent",
            home_dir=tmp_path,
            binary_resolver=_resolver("openclaw"),
            command_runner=runner,
        )

    assert runner.mutation_commands == []
    assert target.is_dir()


def test_private_commit_rejects_wrong_binding_digest_before_native_mutation(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("codex", target)
    plan = _plan("codex", tmp_path, runner)
    ownership = plan["ownership"]

    result = _commit_agent_uninstall(
        "codex",
        expected_install_id=ownership["install_id"],
        expected_bundle_digest=ownership["bundle_digest"],
        expected_binding_digest="0" * 64,
        retained_path=(
            tmp_path
            / ".agency-runtime"
            / "backups"
            / "codex"
            / f"uninstall-{_operation_id('wrong-binding')}"
        ),
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["error"] == "Host profile or native state changed after uninstall planning"
    assert runner.mutation_commands == []
    assert target.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="Windows shim companion binding")
def test_bound_native_command_rejects_changed_cmd_companion_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = ensure_private_directory(
        tmp_path / ".agency-runtime",
        product_owned=True,
    )
    binary_root = ensure_private_directory(tmp_path / "bin", product_owned=True)
    shim = binary_root / "codex.cmd"
    companion = binary_root / "codex.exe"
    shim.write_text("@echo off\r\n", encoding="utf-8")
    companion.write_bytes(b"MZ-planned")
    forbidden_roots = uninstall_subject._host_command_forbidden_roots(runtime_root)
    prepared_argv, projection = uninstall_subject._prepared_launcher(
        [str(shim)],
        runtime_root=runtime_root,
        forbidden_roots=forbidden_roots,
    )
    assert prepared_argv.artifact_paths == (str(companion.resolve()),)
    environment = uninstall_subject._dispatch(
        "_command_environment",
        "codex",
        home_dir=tmp_path,
        current_directory=runtime_root,
        forbidden_roots=forbidden_roots,
    )
    binding = {
        "executable_identity_sha256": uninstall_subject._sha256_json(projection),
        "profile_environment_sha256": uninstall_subject._sha256_json(environment),
        "execution_working_directory": str(runtime_root.resolve()),
        "forbidden_roots_sha256": uninstall_subject._sha256_json(
            [str(root) for root in forbidden_roots]
        ),
    }
    companion.write_bytes(b"MZ-substituted")

    from agency_runtime.core.delegation import backends

    monkeypatch.setattr(
        backends,
        "run_bounded_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("changed launcher must not execute")
        ),
    )
    result = uninstall_subject._run_bound_native_command(
        [str(shim), "plugin", "list", "--json"],
        host="codex",
        binding=binding,
        home_dir=tmp_path,
        command_runner=None,
        timeout=20,
    )

    assert result.ok is False
    assert result.returncode == 70
    assert "Native launcher changed after uninstall planning" in result.stderr


@pytest.mark.skipif(os.name != "nt", reason="Windows shim companion binding")
def test_prepared_launcher_rejects_repository_controlled_companion(tmp_path: Path) -> None:
    runtime_root = ensure_private_directory(
        tmp_path / ".agency-runtime",
        product_owned=True,
    )
    repository_root = ensure_private_directory(tmp_path / "repository", product_owned=True)
    shim = repository_root / "codex.cmd"
    companion = repository_root / "codex.exe"
    shim.write_text("@echo off\r\n", encoding="utf-8")
    companion.write_bytes(b"MZ-repository-controlled")

    with pytest.raises((OSError, PermissionError)):
        uninstall_subject._prepared_launcher(
            [str(shim)],
            runtime_root=runtime_root,
            forbidden_roots=(repository_root.resolve(),),
        )


@pytest.mark.parametrize("host", ["hermes", "openclaw"])
def test_plan_rejects_duplicate_native_plugin_records(
    host: str,
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle(host, tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner(host, target, plugin_record_count=2)

    plan = _plan(host, tmp_path, runner)

    assert plan["ok"] is False
    assert plan["status"] == "blocked"
    assert plan["error"] == "Native Agency plugin inventory is ambiguous"
    assert runner.mutation_commands == []


@pytest.mark.parametrize(
    ("host", "binding"),
    [
        ("openclaw", "wrong"),
        ("codex", "wrong"),
        ("codex", "ambiguous"),
        ("codex", "relative"),
    ],
)
def test_plan_rejects_wrong_or_ambiguous_native_plugin_provenance(
    host: str,
    binding: str,
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle(host, tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner(host, target, plugin_binding=binding)

    plan = _plan(host, tmp_path, runner)

    assert plan["ok"] is False
    assert plan["status"] == "blocked"
    assert plan["error"] == "Native plugin identity is not bound to the managed target"
    assert runner.mutation_commands == []


@pytest.mark.parametrize(
    ("record_count", "binding", "error"),
    [
        (2, "exact", "Native Agency marketplace inventory is ambiguous"),
        (1, "wrong", "Native marketplace identity is not bound to the managed target"),
        (1, "ambiguous", "Native marketplace identity is not bound to the managed target"),
        (1, "relative", "Native marketplace identity is not bound to the managed target"),
    ],
)
def test_plan_rejects_duplicate_or_unbound_marketplace_records(
    record_count: int,
    binding: str,
    error: str,
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("claude", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner(
        "claude",
        target,
        marketplace_record_count=record_count,
        marketplace_binding=binding,
    )

    plan = _plan("claude", tmp_path, runner)

    assert plan["ok"] is False
    assert plan["status"] == "blocked"
    assert plan["error"] == error
    assert runner.mutation_commands == []


def test_openclaw_live_gateway_refuses_plan_without_mutation(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("openclaw", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("openclaw", target, gateway_live=True)

    plan = _plan("openclaw", tmp_path, runner)

    assert plan["ok"] is False
    assert plan["status"] == "blocked"
    assert plan["error"] == "OpenClaw gateway is live; stop it before uninstall"
    assert runner.mutation_commands == []
    assert target.is_dir()


def test_native_mutation_failure_redacts_raw_output(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    secret = "api-key-that-must-not-escape"
    runner = UninstallNativeRunner("codex", target, fail_mutation_secret=secret)
    plan = _plan("codex", tmp_path, runner)
    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", lambda _binding: None)

    result = _apply_prepared_host_uninstall(
        ["codex"],
        expected_plan_digest=_digest([plan]),
        operation_id=_operation_id("redaction"),
        selected_by="agent",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )[0]

    rendered = json.dumps(result, sort_keys=True)
    assert result["ok"] is False
    assert result["status"] == "partial_failure"
    assert result["failed_step"] == "plugin_unregister"
    assert secret not in rendered
    assert "native detail must stay private" not in rendered
    failed = next(step for step in result["native_steps"] if step["name"] == "plugin_unregister")
    assert failed["error"] == "native command failed"
    assert target.is_dir()


def test_marketplace_change_after_plugin_uninstall_blocks_bundle_retirement(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("codex", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("codex", target, remove_marketplace_on_uninstall=True)
    plan = _plan("codex", tmp_path, runner)
    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", lambda _binding: None)

    result = _apply_prepared_host_uninstall(
        ["codex"],
        expected_plan_digest=_digest([plan]),
        operation_id=_operation_id("marketplace-changed"),
        selected_by="agent",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )[0]

    assert result["ok"] is False
    assert result["status"] == "partial_failure"
    assert result["failed_step"] == "marketplace_inventory_detached_changed"
    assert result["retained_path"] is None
    assert target.is_dir()


def test_failed_native_detachment_retains_owned_tree_for_recovery(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    installed = _stage_owned_bundle("hermes", tmp_path)
    target = Path(installed["target"])
    runner = UninstallNativeRunner("hermes", target, sticky_plugin=True)
    plan = _plan("hermes", tmp_path, runner)
    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", lambda _binding: None)

    result = _apply_prepared_host_uninstall(
        ["hermes"],
        expected_plan_digest=_digest([plan]),
        operation_id=_operation_id("sticky-hermes"),
        selected_by="agent",
        home_dir=tmp_path,
        binary_resolver=_resolver("hermes"),
        command_runner=runner,
    )[0]

    assert result["ok"] is False
    assert result["status"] == "partial_failure"
    assert result["failed_step"] == "inventory_detached_present"
    assert result["changed"] is True
    assert result["retained_path"] is None
    assert target.is_dir()
    assert (target / INSTALL_MANIFEST).is_file()


def test_absent_prepared_uninstall_is_idempotent_and_needs_no_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / ".agency-runtime" / "marketplaces" / "codex"
    runner = UninstallNativeRunner("codex", target, present=False)
    plan = _plan("codex", tmp_path, runner)

    def must_not_verify(_binding: object) -> None:
        raise AssertionError("non-mutating absent plan must not request operator verification")

    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", must_not_verify)
    result = _apply_prepared_host_uninstall(
        ["codex"],
        expected_plan_digest=_digest([plan]),
        operation_id=_operation_id("absent"),
        selected_by="agent",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )[0]

    assert plan["ok"] is True
    assert plan["status"] == "not_installed"
    assert plan["would_change"] is False
    assert result["ok"] is True
    assert result["complete"] is True
    assert result["status"] == "not_installed"
    assert result["changed"] is False
    assert runner.mutation_commands == []
    assert target.exists() is False


def test_result_callback_failure_stops_later_host_mutation(
    tmp_path: Path,
    private_installer_launcher: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del private_installer_launcher
    hermes_target = Path(_stage_owned_bundle("hermes", tmp_path)["target"])
    codex_target = Path(_stage_owned_bundle("codex", tmp_path)["target"])
    hermes = UninstallNativeRunner("hermes", hermes_target)
    codex = UninstallNativeRunner("codex", codex_target)
    runner = MultiHostRunner(hermes, codex)
    hosts = ("hermes", "codex")
    plans = [_plan(host, tmp_path, runner, resolver_hosts=hosts) for host in hosts]
    monkeypatch.setattr(prepared, "_require_host_uninstall_authority", lambda _binding: None)
    observed: list[str] = []

    def fail_journal_checkpoint(result: dict[str, Any]) -> None:
        observed.append(str(result["host"]))
        raise RuntimeError("journal checkpoint failed")

    with pytest.raises(RuntimeError, match="journal checkpoint failed"):
        _apply_prepared_host_uninstall(
            list(hosts),
            expected_plan_digest=_digest(plans, selected_by="all"),
            operation_id=_operation_id("callback-stop"),
            selected_by="all",
            home_dir=tmp_path,
            binary_resolver=_resolver(*hosts),
            command_runner=runner,
            on_result=fail_journal_checkpoint,
        )

    assert observed == ["hermes"]
    assert hermes.mutation_commands
    assert hermes_target.exists() is False
    assert codex.mutation_commands == []
    assert codex_target.is_dir()
