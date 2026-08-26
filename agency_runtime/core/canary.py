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
from agency_runtime.core.activation_canary_contract import (
    CODEX_ACTIVATION_CANARY_PROMPT,
)
from agency_runtime.core.bounded_io import (
    FileSizeLimitError,  # noqa: F401 - historical facade attribute
    atomic_write_text,
    read_bounded_regular_file,  # noqa: F401 - monkeypatch compatibility
)
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.canary_judge_provider import (
    configured_canary_child_judge_provider as _configured_canary_child_judge_provider,  # noqa: F401 - compatibility dependency resolved by canary_proof
)
from agency_runtime.core.canary_parent_recruiter_provider import (
    configured_accepted_outcome_parent_recruiter_provider as _configured_accepted_outcome_parent_recruiter_provider,  # noqa: F401 - compatibility dependency resolved by canary_proof
)
from agency_runtime.core.child_delivery_evidence import _discard_verified_host_child_delivery
from agency_runtime.core.config import load_config  # noqa: F401 - compatibility facade
from agency_runtime.core.host_control import SUPPORTED_HOSTS
from agency_runtime.core.installer import (
    PLUGIN_VERSION,  # noqa: F401 - compatibility dependency resolved by canary_proof
    inspect_host_installations,
)
from agency_runtime.core.store.sqlite import (
    Store,  # noqa: F401 - compatibility dependency resolved by canary_proof
    _default_db_path,
)

CANARY_PROMPT = CODEX_ACTIVATION_CANARY_PROMPT
CANARY_EXPECTED_SPECIALIST = "code-reviewer"
CODEX_CANARY_DEVELOPER_INSTRUCTIONS = (
    "This is a bounded Agency Runtime activation canary. If the current task contains "
    "[AGENCY EXACT SPECIALIST EXECUTION v3], you are the sole delegated child: perform "
    "the exact review in the decrypted native child message now, use no tools, and return "
    "one concise sentence. If the current task contains "
    "[AGENCY EXACT TASK EXECUTION v1], perform that legacy exact execution directly, use "
    "no tools, and return one concise sentence. If the current task contains "
    "[AGENCY EXACT SPECIALIST ACTIVATION v1] or "
    "[AGENCY EXACT SPECIALIST ACTIVATION v2], you are the sole delegated child: "
    "this first turn is activation-only; use no tools, perform no review, and return one "
    "concise readiness acknowledgement. "
    "Otherwise you are the parent, and the user explicitly requested exactly one sub-agent "
    "for the whole unit: follow the injected [AGENCY DELEGATION PLAN], require exactly one "
    "row, call spawn_agent exactly once with fork_turns set to none, that row's exact "
    "native_task_name, and exact goal. The selected specialist executes in that initial "
    "child turn. Call wait_agent once with a 60000 ms timeout for the child to become "
    "terminal. Do not call followup_task. Never retry any collaboration call. If the spawn "
    "fails or the wait times "
    "out, report that result and stop the protocol. "
    "Use no other tools. Return the child's conclusion with the required Agency header. "
    "Do not modify files, call external services, or expose secrets."
)
CODEX_NATIVE_ONLY_DEVELOPER_INSTRUCTIONS = (
    "This is a bounded Agency Runtime native-only installation canary. Reply with one "
    "concise plain confirmation. Do not delegate, use tools, emit an Agency header, "
    "modify files, call external services, or expose secrets."
)
NATIVE_ONLY_CANARY_PROMPT = (
    "Agency Runtime native-only installation canary. Reply with a concise plain "
    "confirmation. Do not emit an Agency header, modify files, call external "
    "services, use tools, or expose secrets."
)
RECEIPT_CAPABLE_HOSTS = frozenset({"hermes"})
SAFE_CANARY_HOSTS = frozenset({"codex", "claude"})
ISOLATED_CANARY_HOSTS = SAFE_CANARY_HOSTS
CANARY_MODES = frozenset({"agency", "native-only"})
CANARY_PROFILE_SCOPES = frozenset({"isolated-profile", "current-profile"})
CANARY_TRUST_MODES = frozenset({"attended", "autonomous_bypass", "managed_policy"})
MAX_CANARY_TIMEOUT_SECONDS = 600.0
CODEX_CURRENT_PROFILE_EXEC_OPTIONS = (
    "--json",
    "--color",
    "never",
    "--ignore-rules",
    "--strict-config",
    "--enable",
    "multi_agent_v2",
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
    "-c",
    "agents.enabled=true",
    "-c",
    f"developer_instructions={json.dumps(CODEX_CANARY_DEVELOPER_INSTRUCTIONS)}",
    "--skip-git-repo-check",
    "-",
)
CODEX_CANARY_EXEC_OPTIONS = (
    *CODEX_CURRENT_PROFILE_EXEC_OPTIONS[:-1],
    "--dangerously-bypass-hook-trust",
    "-",
)
CODEX_NATIVE_ONLY_CURRENT_PROFILE_EXEC_OPTIONS = (
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
    "-c",
    "agents.enabled=false",
    "-c",
    f"developer_instructions={json.dumps(CODEX_NATIVE_ONLY_DEVELOPER_INSTRUCTIONS)}",
    "--skip-git-repo-check",
    "-",
)
CODEX_NATIVE_ONLY_CANARY_EXEC_OPTIONS = (
    *CODEX_NATIVE_ONLY_CURRENT_PROFILE_EXEC_OPTIONS[:-1],
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
_project_isolated_runtime_control = _backends.project_isolated_runtime_control
_prepare_private_host_home = _backends.prepare_private_host_home
_project_isolated_codex_workspace_trust = _backends.project_isolated_codex_workspace_trust
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
    master_enabled: bool = True,
    profile_scope: str = "isolated-profile",
    require_existing_store: bool = False,
    require_exact_activation_rollout: bool = False,
    hook_trust_inspector: Callable[..., Mapping[str, Any]] | None = None,
    trust_mode: str = "attended",
    child_judge_provider: str = "",
    child_judge_transport: str = "",
    parent_recruiter_provider: str = "",
    parent_recruiter_transport: str = "",
):
    return _backends.backend(
        host,
        db_path=db_path,
        timeout=timeout,
        native=native,
        resolver=resolver,
        runner=runner,
        environ=environ,
        master_enabled=master_enabled,
        profile_scope=profile_scope,
        require_existing_store=require_existing_store,
        require_exact_activation_rollout=require_exact_activation_rollout,
        hook_trust_inspector=hook_trust_inspector,
        trust_mode=trust_mode,
        child_judge_provider=child_judge_provider,
        child_judge_transport=child_judge_transport,
        parent_recruiter_provider=parent_recruiter_provider,
        parent_recruiter_transport=parent_recruiter_transport,
    )


def _read_canary_master_control() -> tuple[dict[str, Any], str]:
    """Read the real profile's master switch without fail-enabled fallback."""
    from agency_runtime.core.runtime_control import read_authoritative_runtime_control

    return read_authoritative_runtime_control(use_cache=False)


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


def _attach_master_readiness(
    report: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any] | None:
    expected_enabled = mode == "agency"
    try:
        document, transport = _read_canary_master_control()
    except Exception:
        report["master_control"] = {"expected_enabled": expected_enabled}
        report["unmet_prerequisites"].append(
            "authoritative Agency master control could not be read"
        )
        report["ready"] = False
        return None
    report["master_control"] = {
        "enabled": bool(document["enabled"]),
        "generation": int(document["generation"]),
        "source": str(document["source"]),
        "transport": transport,
        "expected_enabled": expected_enabled,
    }
    if bool(document["enabled"]) is not expected_enabled:
        required = "enabled" if expected_enabled else "disabled"
        report["unmet_prerequisites"].append(
            f"Agency master control must be {required} for {mode} mode"
        )
    report["ready"] = not report["unmet_prerequisites"]
    return document


def _master_control_is_unchanged(
    report: dict[str, Any],
    expected: Mapping[str, Any],
    *,
    read_failure: str,
    drift_failure: str,
) -> bool:
    try:
        current, _transport = _read_canary_master_control()
    except Exception:
        report["unmet_prerequisites"].append(read_failure)
        return False
    if current != expected:
        report["unmet_prerequisites"].append(drift_failure)
        return False
    return True


def _complete_successful_canary(
    report: dict[str, Any],
    *,
    host: str,
    mode: str,
    path: Path,
    inspector: Callable[[str], dict[str, Any]],
    assessment: Any,
    master_before: Mapping[str, Any],
    preparation: Any,
    proof: Any,
    evidence: Mapping[str, Any],
    trust_mode: str = "attended",
) -> None:
    current = _assess_readiness(
        host,
        path,
        inspector,
        profile_scope=assessment.profile_scope,
    )
    if not _attestation_identity_is_current(assessment, current):
        report["unmet_prerequisites"].append(
            "native host or managed bundle identity changed or became unverified during canary"
        )
        report["attestation_persisted"] = False
        return
    if not _master_control_is_unchanged(
        report,
        master_before,
        read_failure=(
            "authoritative Agency master control could not be verified before completion"
        ),
        drift_failure="Agency master control changed before canary completion",
    ):
        report["attestation_persisted"] = False
        return
    if (
        mode == "native-only"
        or host != "codex"
        or assessment.profile_scope != "current-profile"
        or trust_mode == "autonomous_bypass"
    ):
        report["attestation_persisted"] = False
        report["canary_passed"] = True
        return
    if preparation.store is None:
        report["unmet_prerequisites"].append("canary attestation store is unavailable")
        report["attestation_persisted"] = False
        return
    attestation, error = _persist_attestation(
        preparation.store,
        _attestation_payload(
            host,
            proof=proof,
            evidence=evidence,
            assessment=current,
            passed_at=report["sampled_at"],
        ),
    )
    if error:
        report["unmet_prerequisites"].append(error)
        report["attestation_persisted"] = False
        return
    report["attestation_persisted"] = True
    report["attestation"] = attestation
    report["canary_passed"] = True


def _terminate_failed_canary_runs(
    report: dict[str, Any],
    *,
    host: str,
    preparation: Any,
    evidence: Mapping[str, Any] | None,
) -> None:
    """Close only active runs bound to this exact failed canary request."""

    if preparation.store is None or preparation.expected_query_hash is None:
        return
    exact_closer = getattr(preparation.store, "fail_canary_runs_for_request", None)
    if callable(exact_closer):
        try:
            closed = list(
                exact_closer(
                    host=host,
                    request_fingerprint=preparation.expected_query_hash,
                )
            )
        except Exception:
            report["unmet_prerequisites"].append(
                "failed canary runs could not be terminated by exact request identity"
            )
            return
        report["failed_run_cleanup"] = {
            "candidate_count": len(closed),
            "closed_count": len(closed),
            "closed_run_ids": closed,
            "scope": "exact_request_fingerprint",
        }
        return
    if not isinstance(evidence, Mapping):
        return
    new_ids = evidence.get("new_ids")
    run_ids = new_ids.get("runs", []) if isinstance(new_ids, Mapping) else []
    run = evidence.get("run")
    if isinstance(run, Mapping) and run.get("id"):
        run_ids = list(dict.fromkeys([*run_ids, str(run["id"])]))
    closed: list[str] = []
    errors = 0
    for run_id in run_ids:
        try:
            if preparation.store.fail_canary_run(
                str(run_id),
                host=host,
                request_fingerprint=preparation.expected_query_hash,
            ):
                closed.append(str(run_id))
        except Exception:
            errors += 1
    report["failed_run_cleanup"] = {
        "candidate_count": len(run_ids),
        "closed_count": len(closed),
        "closed_run_ids": closed,
    }
    if errors:
        report["unmet_prerequisites"].append(
            "one or more failed canary runs could not be terminated"
        )


def _report_failed_canary_invocation(
    report: dict[str, Any],
    *,
    host: str,
    preparation: Any,
    evidence: Mapping[str, Any] | None,
    error: str,
) -> None:
    if evidence is not None:
        report["evidence"] = evidence
    _terminate_failed_canary_runs(
        report,
        host=host,
        preparation=preparation,
        evidence=evidence,
    )
    report["unmet_prerequisites"].append(error)


def _invalidate_prior_current_profile_attestation(
    report: dict[str, Any],
    *,
    host: str,
    profile_scope: str,
    store: Any,
) -> bool:
    """Make an explicitly requested current-profile recheck fail closed."""

    if profile_scope != "current-profile":
        return True
    invalidator = getattr(store, "clear_host_canary_attestation", None)
    if not callable(invalidator):
        report["unmet_prerequisites"].append(
            "prior current-profile attestation could not be invalidated before verification"
        )
        return False
    try:
        report["prior_attestation_invalidated"] = bool(invalidator(host))
    except Exception:
        report["unmet_prerequisites"].append(
            "prior current-profile attestation could not be invalidated before verification"
        )
        return False
    return True


def _validate_canary_request(
    host: str,
    *,
    mode: str,
    profile_scope: str,
    trust_mode: str = "attended",
) -> None:
    """Reject unsupported canary combinations before any host or Store access."""

    if host not in SUPPORTED_HOSTS:
        raise ValueError(f"unsupported host: {host}")
    if mode not in CANARY_MODES:
        raise ValueError(f"unsupported canary mode: {mode}")
    if profile_scope not in CANARY_PROFILE_SCOPES:
        raise ValueError(f"unsupported canary profile scope: {profile_scope}")
    if not isinstance(trust_mode, str) or trust_mode not in CANARY_TRUST_MODES:
        raise ValueError(f"unsupported canary trust mode: {trust_mode}")
    if profile_scope == "current-profile" and (host != "codex" or mode != "agency"):
        raise ValueError("current-profile canaries support Codex Agency mode only")
    if trust_mode == "autonomous_bypass" and (
        host != "codex" or mode != "agency" or profile_scope != "current-profile"
    ):
        raise ValueError(
            "autonomous bypass canaries support Codex Agency current-profile mode only"
        )
    if trust_mode == "managed_policy" and (
        host != "codex" or mode != "agency" or profile_scope != "current-profile"
    ):
        raise ValueError("managed-policy canaries support Codex Agency current-profile mode only")


def run_canary(
    host: str,
    *,
    execute: bool = False,
    confirm: str = "",
    db_path: str | Path | None = None,
    config_path: str | Path | None = None,
    timeout: float = 120,
    mode: str = "agency",
    profile_scope: str = "isolated-profile",
    require_existing_store: bool = False,
    trust_mode: str = "attended",
    inspector: Callable[[str], dict[str, Any]] = _default_inspector,
    backend_factory: Callable[..., Any] = _backend,
) -> dict[str, Any]:
    """Build read-only readiness or run an exact-confirmed evidence canary."""
    if type(require_existing_store) is not bool:
        raise TypeError("require_existing_store must be a boolean")
    if require_existing_store and (host != "codex" or profile_scope != "current-profile"):
        raise ValueError("existing-store canaries support Codex current-profile only")
    _validate_canary_request(
        host,
        mode=mode,
        profile_scope=profile_scope,
        trust_mode=trust_mode,
    )
    timeout = _validated_timeout(timeout)
    path = Path(db_path).expanduser() if db_path else _default_db_path()
    bound_config_path = Path(config_path).expanduser() if config_path is not None else None
    assessment = _assess_readiness(host, path, inspector, profile_scope=profile_scope)
    report = _readiness_report(host, assessment, mode=mode, trust_mode=trust_mode)
    master_before = _attach_master_readiness(report, mode=mode)
    if master_before is None:
        return report
    if not execute:
        return report

    expected = str(report["execute_confirmation"])
    if confirm != expected:
        report["unmet_prerequisites"].append(f"confirmation must exactly match: {expected}")
        return report
    if report["unmet_prerequisites"]:
        return report
    preparation = _prepare_live_invocation(
        host,
        path=path,
        config_path=bound_config_path,
        timeout=timeout,
        native=assessment.native,
        backend_factory=backend_factory,
        master_enabled=mode == "agency",
        mode=mode,
        profile_scope=assessment.profile_scope,
        require_existing_store=require_existing_store,
        trust_mode=trust_mode,
    )
    if preparation.error:
        report["unmet_prerequisites"].append(preparation.error)
        return report
    if preparation.prompt is None or preparation.expected_query_hash is None:
        report["unmet_prerequisites"].append(
            "safe canary preparation returned incomplete invocation state"
        )
        return report
    if not _invalidate_prior_current_profile_attestation(
        report,
        host=host,
        profile_scope=assessment.profile_scope,
        store=preparation.store,
    ):
        return report
    report["live_attempted"] = True
    outcome = _invoke_and_collect_evidence(
        preparation,
        host=host,
        path=path,
        prompt=preparation.prompt,
        expected_query_hash=preparation.expected_query_hash,
        mode=mode,
    )
    if outcome.error:
        _discard_verified_host_child_delivery(outcome.host_child_delivery)
        _report_failed_canary_invocation(
            report,
            host=host,
            preparation=preparation,
            evidence=outcome.evidence,
            error=outcome.error,
        )
        return report
    if outcome.result is None or outcome.evidence is None:
        _discard_verified_host_child_delivery(outcome.host_child_delivery)
        report["unmet_prerequisites"].append(
            "safe host invocation returned incomplete evidence state"
        )
        return report
    if not _master_control_is_unchanged(
        report,
        master_before,
        read_failure=("authoritative Agency master control could not be re-read after invocation"),
        drift_failure="Agency master control changed during the canary invocation",
    ):
        _discard_verified_host_child_delivery(outcome.host_child_delivery)
        _terminate_failed_canary_runs(
            report,
            host=host,
            preparation=preparation,
            evidence=outcome.evidence,
        )
        return report
    proof = _evaluate_proof(
        host,
        result=outcome.result,
        evidence=outcome.evidence,
        default_profile_scope=assessment.profile_scope,
        mode=mode,
        host_child_delivery=outcome.host_child_delivery,
    )
    report.update(
        {
            "sampled_at": _utc_now(),
            "live_attempted": True,
            "invocation": proof.invocation,
            "evidence": outcome.evidence,
        }
    )
    actual_trust_mode = outcome.result.get("trust_mode")
    if isinstance(actual_trust_mode, str) and actual_trust_mode in CANARY_TRUST_MODES:
        report["trust_mode"] = actual_trust_mode
    report["trust_bypass_used"] = outcome.result.get("trust_bypass_used") is True
    report["unmet_prerequisites"].extend(proof.failures)
    if proof.passed:
        _complete_successful_canary(
            report,
            host=host,
            mode=mode,
            path=path,
            inspector=inspector,
            assessment=assessment,
            master_before=master_before,
            preparation=preparation,
            proof=proof,
            evidence=outcome.evidence,
            trust_mode=str(report["trust_mode"]),
        )
    else:
        _terminate_failed_canary_runs(
            report,
            host=host,
            preparation=preparation,
            evidence=outcome.evidence,
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or explicitly execute an Agency Runtime host canary"
    )
    parser.add_argument("host", choices=SUPPORTED_HOSTS)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=sorted(CANARY_MODES), default="agency")
    parser.add_argument(
        "--profile-scope",
        choices=sorted(CANARY_PROFILE_SCOPES),
        default="isolated-profile",
    )
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
        mode=args.mode,
        profile_scope=args.profile_scope,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        atomic_write_text(Path(args.output), rendered)
    sys.stdout.write(rendered)
    return 0 if (report["canary_passed"] if args.execute else report["ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
