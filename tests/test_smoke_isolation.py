"""Regression tests for smoke isolation from the operator profile."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.core import smoke
from agency_runtime.core.config import load_config, reset_config_cache


def test_smoke_all_hosts_ignores_cached_real_store_path(
    tmp_path: Path,
    monkeypatch,
    private_installer_launcher,
) -> None:
    operator_db = tmp_path / "operator-profile" / "agency.db"
    config_path = tmp_path / "operator.yaml"
    config_path.write_text(
        f"store:\n  db_path: {operator_db.as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    reset_config_cache()
    observed_paths: list[Path] = []
    real_smoke_generated_plugin = smoke._smoke_generated_plugin

    def inspect_isolated_host(host: str, _tmp_home: Path) -> dict[str, str]:
        resolved = load_config().store.resolved_path()
        assert resolved != operator_db
        observed_paths.append(resolved)
        if host == "hermes":
            return real_smoke_generated_plugin(host, _tmp_home)
        return {"host": host}

    monkeypatch.setattr(smoke, "_smoke_generated_plugin", inspect_isolated_host)
    monkeypatch.setattr(
        smoke,
        "run_host_parity_eval",
        lambda: {"passed": True, "passed_count": 1, "failed_count": 0},
    )
    try:
        assert load_config().store.resolved_path() == operator_db

        report = smoke.run_smoke(all_hosts=True)

        assert report["passed"] is True, json.dumps(report, indent=2)
        assert len(observed_paths) == len(smoke.HOSTS)
        assert len(set(observed_paths)) == 1
        assert operator_db.exists() is False
    finally:
        reset_config_cache()
