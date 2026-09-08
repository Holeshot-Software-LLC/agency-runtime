"""Real private CLI uninstall without replacing its authority or commit boundary."""

from __future__ import annotations

import json
import sqlite3
from functools import partial
from pathlib import Path

import pytest

from agency_runtime.cli import install_commands, uninstall_commands
from agency_runtime.cli.main import build_parser
from agency_runtime.core import installer, runtime_control, runtime_staleness
from agency_runtime.core.installer_contracts import INSTALL_MANIFEST
from agency_runtime.core.installer_zcode import (
    inspect_zcode_registration,
    zcode_config_path,
    zcode_registration_state_path,
)
from agency_runtime.core.prepared_host_uninstall import _apply_prepared_host_uninstall
from agency_runtime.core.private_paths import ensure_private_directory
from agency_runtime.core.store.sqlite import Store


def _tree_bytes(root: Path, *, ignore: tuple[Path, ...] = ()) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path not in ignore
    }


def _store_contents(path: Path) -> tuple[str, ...]:
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        return tuple(connection.iterdump())
    finally:
        connection.close()


def test_private_zcode_cli_uninstall_preserves_owner_data_with_real_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    private_installer_launcher: tuple[Path, Path],
) -> None:
    """Install, reject a wrong digest, then remove only the owned integration.

    Seams select private filesystem roots and an unavailable native executable;
    they do not grant authority or replace the real journal, binding primitives,
    lifecycle locks, replanning/digest comparison, config merge, or retirement.
    The launcher fixture copies real package bytes to a private test namespace.
    No owner HOME/host-home environment variable is reassigned.
    """
    del private_installer_launcher
    private_home = ensure_private_directory(tmp_path / "private-home")
    runtime_root = ensure_private_directory(private_home / ".agency-runtime")
    native_config = zcode_config_path(home_dir=private_home)
    ensure_private_directory(native_config.parent)
    unrelated_config = {
        "theme": "keep-me",
        "hooks": {
            "enabled": False,
            "events": {"UnrelatedEvent": [{"name": "keep-me"}]},
        },
    }
    native_config.write_text(json.dumps(unrelated_config), encoding="utf-8")
    history = native_config.parent / "history.txt"
    history.write_text("Preserve prior owner history.\n", encoding="utf-8")
    config_path = runtime_root / "agency.yaml"
    database_path = runtime_root / "agency.db"
    # Read-only Store inspection may materialize SQLite coordination sidecars.
    # Compare durable bytes here and all logical database contents separately.
    sqlite_sidecars = tuple(Path(f"{database_path}-{suffix}") for suffix in ("wal", "shm"))
    private_bytes = partial(_tree_bytes, private_home, ignore=sqlite_sidecars)
    config_path.write_text(
        "profile: standard\n"
        f'store:\n  db_path: "{database_path.as_posix()}"\n'
        "providers: []\n"
        'judge:\n  model: ""\n  base_url: ""\n  api_key: ""\n  api_key_env: ""\n'
        "  ollama_mode: false\n"
        "ollama:\n  enabled: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AGENCY_DB_PATH", str(database_path))

    # These public adapters have explicit home seams; retain their actual work.
    def no_native_executable(_name: str) -> None:
        return None

    monkeypatch.setattr(
        installer,
        "install_agent_adapter",
        partial(
            installer.install_agent_adapter,
            home_dir=private_home,
            binary_resolver=no_native_executable,
        ),
    )
    actual_control_path = runtime_control.runtime_control_path
    monkeypatch.setattr(
        runtime_control,
        "runtime_control_path",
        lambda *, home_dir=None: actual_control_path(
            home_dir=private_home if home_dir is None else home_dir
        ),
    )

    def private_launchers(name: str) -> Path:
        assert name == "launchers"
        return ensure_private_directory(runtime_root / name)

    def private_operations(name: str) -> Path:
        assert name == "operations"
        return ensure_private_directory(runtime_root / name)

    monkeypatch.setattr(runtime_staleness, "private_runtime_directory", private_launchers)
    monkeypatch.setattr(uninstall_commands, "private_runtime_directory", private_operations)
    parser = build_parser()
    install_args = parser.parse_args(
        ["install", "--agent", "zcode", "--config", str(config_path), "--no-dashboard", "--json"]
    )
    assert install_commands.cmd_install(install_args) == 0
    install_report = json.loads(capsys.readouterr().out)
    assert install_report["complete"] is True
    assert install_report["config_path"] == str(config_path)
    assert install_report["roster_added"] > 0
    assert install_report["dashboard"]["status"] == "opted_out"
    installed = install_report["hosts"][0]
    assert installed["host"] == "zcode"
    assert installed["registered"] is True
    target = Path(installed["target"])
    assert target.is_relative_to(private_home)
    installed_tree = _tree_bytes(target)
    assert INSTALL_MANIFEST in installed_tree
    registration = inspect_zcode_registration(target, home_dir=private_home)
    assert registration["owned_handler_count"] > 0
    retained_native_config = json.loads(native_config.read_text(encoding="utf-8"))
    assert retained_native_config["theme"] == unrelated_config["theme"]
    assert retained_native_config["hooks"]["enabled"] is False
    # Shared hook settings (including install's timeout floor) are not owned
    # event handlers. Uninstall removes the latter and preserves the former.
    retained_native_config["hooks"]["events"] = unrelated_config["hooks"]["events"]

    runtime_store = Store(config_path=config_path)
    assert runtime_store.get_active_roster()
    trace_id = "ar189-preserved-run"
    runtime_store.create_run(trace_id=trace_id, session_id="ar189-history", host="zcode")
    runtime_store.record_import_event("ar189-retained-history", detail="Keep this evidence")
    store_before = _store_contents(database_path)
    owner_config_before = config_path.read_bytes()
    history_before = history.read_bytes()
    before_plan = private_bytes()

    # Keep the production writer and apply chain; only thread the private home
    # through the existing injectable host boundary used by the CLI dependency.
    dependencies = uninstall_commands.UninstallDependencies(
        plan_host=partial(
            installer.plan_agent_uninstall,
            home_dir=private_home,
            binary_resolver=no_native_executable,
        ),
        apply_prepared=partial(
            _apply_prepared_host_uninstall,
            home_dir=private_home,
            binary_resolver=no_native_executable,
        ),
    )

    def uninstall(*arguments: str) -> tuple[int, dict]:
        parsed = parser.parse_args(["uninstall", "--agent", "zcode", "--json", *arguments])
        result = uninstall_commands.cmd_uninstall(parsed, dependencies=dependencies)
        return result, json.loads(capsys.readouterr().out)

    code, plan = uninstall("--dry-run")
    assert code == 0
    assert plan["hosts"][0]["status"] == "planned"
    assert plan["hosts"][0]["would_change"] is True
    assert plan["selected_hosts"] == ["zcode"]
    assert private_bytes() == before_plan
    assert not (runtime_root / "operations").exists()

    code, refused = uninstall("--confirm-plan", "0" * 64)
    assert code != 0
    assert refused["confirmation_required"] is True
    assert private_bytes() == before_plan
    assert not (runtime_root / "operations").exists()

    code, applied = uninstall("--confirm-plan", plan["plan_digest"])
    assert code == 0, applied
    assert applied["complete"] is True
    result = applied["hosts"][0]
    assert result["status"] == "uninstalled"
    assert result["changed"] is True
    assert result["agency_configuration_removed"] is False
    assert not target.exists()
    retained = runtime_root / "backups" / "zcode" / f"uninstall-{applied['operation_id']}"
    assert result["retained_path"] == str(retained)
    assert result["recovery_backup"] == str(retained)
    assert str(retained) in result["recovery"]
    assert _tree_bytes(retained) == installed_tree
    assert json.loads(native_config.read_text(encoding="utf-8")) == retained_native_config
    assert not zcode_registration_state_path(home_dir=private_home).exists()
    assert inspect_zcode_registration(target, home_dir=private_home)["owned_handler_count"] == 0
    assert config_path.read_bytes() == owner_config_before
    assert history.read_bytes() == history_before
    assert _store_contents(database_path) == store_before
    assert runtime_store.get_run(trace_id) is not None

    journal_path = Path(applied["journal_path"])
    assert journal_path.parent == runtime_root / "operations"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    assert journal["status"] == "complete"
    assert journal["plan_digest"] == plan["plan_digest"]
    assert journal["outcomes"][0]["status"] == "uninstalled"
    before_noop = private_bytes()
    code, absent = uninstall("--dry-run")
    assert code == 0
    assert absent["hosts"][0]["status"] == "not_installed"
    code, repeated = uninstall("--confirm-plan", absent["plan_digest"])
    assert code == 0
    assert repeated["hosts"][0]["status"] == "not_installed"
    assert private_bytes() == before_noop
    assert _store_contents(database_path) == store_before
    print(
        json.dumps(
            {
                "scope": "real private ZCode CLI install and uninstall; no native process",
                "install_status": installed["status"],
                "initial_owned_handlers": registration["owned_handler_count"],
                "dry_run_no_owned_state_changes": True,
                "wrong_digest_no_owned_state_changes": True,
                "apply": applied,
                "roster_and_store_contents_preserved": True,
                "owner_config_and_history_preserved": True,
                "retained_bundle_exact": True,
                "repeat_uninstall_no_owned_state_changes": True,
                "sqlite_read_sidecars_excluded_from_byte_snapshot": [
                    path.name for path in sqlite_sidecars
                ],
                "authority_and_commit_boundaries_unpatched": True,
            },
            sort_keys=True,
        )
    )
