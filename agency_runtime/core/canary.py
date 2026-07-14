"""Readiness and explicitly confirmed live canaries for native agent hosts.

Credential-isolated host execution and proof orchestration live in focused
internal modules.  This facade retains the established public and monkeypatch
surface while keeping the live-canary trust boundary reviewable.
"""

from __future__ import annotations

import argparse
import json
import math
import os  # noqa: F401 - compatibility dependency resolved by canary_backends
import platform  # noqa: F401 - compatibility dependency resolved by canary_proof
import secrets  # noqa: F401 - compatibility dependency resolved by canary_proof
import shutil
import sqlite3
import sys
import time  # noqa: F401 - compatibility clock resolved by canary_backends
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core import canary_backends as _backends
from agency_runtime.core import canary_proof as _proof
from agency_runtime.core.bounded_io import (
    FileSizeLimitError,  # noqa: F401 - historical facade attribute
    read_bounded_regular_file,  # noqa: F401 - monkeypatch compatibility
)
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.host_control import SUPPORTED_HOSTS
from agency_runtime.core.installer import (
    PLUGIN_VERSION,  # noqa: F401 - compatibility dependency resolved by canary_proof
    inspect_host_installations,
)
from agency_runtime.core.store.sqlite import (
    Store,  # noqa: F401 - compatibility dependency resolved by canary_proof
    _default_db_path,
)

CANARY_PROMPT = (
    "Agency Runtime live installation canary. Reply with a concise confirmation "
    "and obey the installed Agency Runtime routing and final-response contract. "
    "Do not modify files, call external services, or expose secrets."
)
RECEIPT_CAPABLE_HOSTS = frozenset({"hermes"})
SAFE_CANARY_HOSTS = frozenset({"codex", "claude"})
ISOLATED_CANARY_HOSTS = SAFE_CANARY_HOSTS
MAX_CANARY_TIMEOUT_SECONDS = 600.0
CODEX_CANARY_EXEC_OPTIONS = (
    "--json",
    "--color",
    "never",
    "--ephemeral",
    "--ignore-rules",
    "--strict-config",
    "--sandbox",
    "read-only",
    "-c",
    "features.shell_tool=false",
    "-c",
    "features.unified_exec=false",
    "-c",
    'web_search="disabled"',
    "-c",
    "apps._default.enabled=false",
    "-c",
    "mcp_servers={}",
    "--skip-git-repo-check",
    "--dangerously-bypass-hook-trust",
    "-",
)


def _load_canary_json(value: str | bytes, *, maximum_bytes: int) -> Any:
    """Parse one bounded subprocess payload without accepting ambiguous JSON."""
    return safe_load_bounded_json(
        value,
        maximum_bytes=maximum_bytes,
        maximum_depth=32,
        maximum_nodes=5_000,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validated_timeout(value: float) -> float:
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0 or timeout > MAX_CANARY_TIMEOUT_SECONDS:
        raise ValueError(
            f"timeout must be greater than 0 and at most {MAX_CANARY_TIMEOUT_SECONDS:g} seconds"
        )
    return timeout


def _read_control_without_writes(db_path: Path, host: str) -> dict[str, Any]:
    """Read soft control through SQLite read-only mode; absent state defaults on."""
    default = {
        "host": host,
        "enabled": True,
        "updated_at": None,
        "source": "default",
    }
    if not db_path.is_file():
        return default
    uri = db_path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'host_controls'"
            ).fetchone()
            if exists is None:
                return default
            row = conn.execute(
                "SELECT host, enabled, updated_at, source FROM host_controls WHERE host = ?",
                (host,),
            ).fetchone()
            if row is None:
                return default
            return {
                "host": str(row["host"]),
                "enabled": bool(row["enabled"]),
                "updated_at": str(row["updated_at"]),
                "source": str(row["source"]),
            }
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return {**default, "enabled": None, "source": "unverified"}


def _default_inspector(host: str) -> dict[str, Any]:
    return inspect_host_installations(hosts=[host])[0]


# Credential-isolated backend compatibility surface.
_SafeCodexCanaryBackend = _backends.SafeCodexCanaryBackend
_SafeClaudeCanaryBackend = _backends.SafeClaudeCanaryBackend
_copy_bounded_auth = _backends.copy_bounded_auth
_codex_isolated_plugin_enabled = _backends.codex_isolated_plugin_enabled
_isolated_canary_environment = _backends.isolated_canary_environment
_prepare_private_host_home = _backends.prepare_private_host_home
_process_succeeded = _backends.process_succeeded
_codex_output = _backends.codex_output
_codex_canary_record = _backends.codex_canary_record
_claude_canary_record = _backends.claude_canary_record
_remaining_canary_timeout = _backends.remaining_timeout
_managed_target = _backends.managed_target
_codex_marketplace = _backends.codex_marketplace
_claude_plugin_dir = _backends.claude_plugin_dir
_source_home = _backends.source_home


def _backend(
    host: str,
    *,
    db_path: Path,
    timeout: float,
    native: Mapping[str, Any] | None = None,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] | None = None,
    environ: Mapping[str, str] | None = None,
):
    return _backends.backend(
        host,
        db_path=db_path,
        timeout=timeout,
        native=native,
        resolver=resolver,
        runner=runner,
        environ=environ,
    )


# Readiness and durable-proof compatibility surface.
_ids = _proof.ids
_evidence_delta = _proof.evidence_delta
_response_text = _proof.response_text
_evidence_summary = _proof.evidence_summary
_ReadinessAssessment = _proof.ReadinessAssessment
_LivePreparation = _proof.LivePreparation
_InvocationOutcome = _proof.InvocationOutcome
_CanaryProof = _proof.CanaryProof
_assess_readiness = _proof.assess_readiness
_readiness_report = _proof.readiness_report
_prepare_live_invocation = _proof.prepare_live_invocation
_invoke_and_collect_evidence = _proof.invoke_and_collect_evidence
_profile_is_proven = _proof.profile_is_proven
_render_isolated_plugin = _proof.render_isolated_plugin
_proof_failures = _proof.proof_failures
_evaluate_proof = _proof.evaluate_proof
_attestation_payload = _proof.attestation_payload
_attestation_identity_is_current = _proof.attestation_identity_is_current
_persist_attestation = _proof.persist_attestation


def run_canary(
    host: str,
    *,
    execute: bool = False,
    confirm: str = "",
    db_path: str | Path | None = None,
    timeout: float = 120,
    inspector: Callable[[str], dict[str, Any]] = _default_inspector,
    backend_factory: Callable[..., Any] = _backend,
) -> dict[str, Any]:
    """Build a nonmutating readiness report or run an exact-confirmed canary."""
    if host not in SUPPORTED_HOSTS:
        raise ValueError(f"unsupported host: {host}")
    timeout = _validated_timeout(timeout)
    path = Path(db_path).expanduser() if db_path else _default_db_path()
    assessment = _assess_readiness(host, path, inspector)
    report = _readiness_report(host, assessment)
    if not execute:
        return report

    expected = f"RUN LIVE {host} CANARY"
    if confirm != expected:
        report["unmet_prerequisites"].append(f"confirmation must exactly match: {expected}")
        return report
    if assessment.unmet:
        return report
    preparation = _prepare_live_invocation(
        host,
        path=path,
        timeout=timeout,
        native=assessment.native,
        backend_factory=backend_factory,
    )
    if preparation.error:
        report["unmet_prerequisites"].append(preparation.error)
        return report
    assert preparation.prompt is not None
    assert preparation.expected_query_hash is not None
    report["live_attempted"] = True
    outcome = _invoke_and_collect_evidence(
        preparation,
        host=host,
        path=path,
        prompt=preparation.prompt,
        expected_query_hash=preparation.expected_query_hash,
    )
    if outcome.error:
        report["unmet_prerequisites"].append(outcome.error)
        return report
    assert outcome.result is not None
    assert outcome.evidence is not None
    proof = _evaluate_proof(
        host,
        result=outcome.result,
        evidence=outcome.evidence,
        default_profile_scope=assessment.profile_scope,
    )
    report.update(
        {
            "sampled_at": _utc_now(),
            "live_attempted": True,
            "invocation": proof.invocation,
            "evidence": outcome.evidence,
        }
    )
    report["unmet_prerequisites"].extend(proof.failures)
    if proof.passed:
        current = _assess_readiness(host, path, inspector)
        if not _attestation_identity_is_current(assessment, current):
            report["unmet_prerequisites"].append(
                "native host or managed bundle identity changed or became unverified during canary"
            )
            report["attestation_persisted"] = False
            return report
        assert preparation.store is not None
        attestation, error = _persist_attestation(
            preparation.store,
            _attestation_payload(
                host,
                proof=proof,
                evidence=outcome.evidence,
                assessment=current,
                passed_at=report["sampled_at"],
            ),
        )
        if error:
            report["unmet_prerequisites"].append(error)
            report["attestation_persisted"] = False
        else:
            report["attestation_persisted"] = True
            report["attestation"] = attestation
            report["canary_passed"] = True
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or explicitly execute an Agency Runtime host canary"
    )
    parser.add_argument("host", choices=SUPPORTED_HOSTS)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--db", default=None)
    parser.add_argument("--timeout", type=_validated_timeout, default=120.0)
    parser.add_argument("--output", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_canary(
        args.host,
        execute=args.execute,
        confirm=args.confirm,
        db_path=args.db,
        timeout=args.timeout,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if (report["canary_passed"] if args.execute else report["ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
