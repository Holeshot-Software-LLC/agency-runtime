"""Regression tests for smoke isolation from the operator profile."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.smoke import run_smoke


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
    try:
        assert load_config().store.resolved_path() == operator_db

        report = run_smoke(all_hosts=True)

        assert report["passed"] is True, json.dumps(report, indent=2)
        assert operator_db.exists() is False
    finally:
        reset_config_cache()
