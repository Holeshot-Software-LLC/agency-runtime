"""Readiness, evidence correlation, and durable proof for host canaries."""

from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _facade():
    """Resolve canary dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import canary

    return canary


def ids(activity: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    return {
        name: {str(row.get("id")) for row in rows if row.get("id")}
        for name, rows in activity.items()
    }


def evidence_delta(
    before: dict[str, list[dict[str, Any]]],
    after: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    previous = _facade()._ids(before)
    return {
        name: [row for row in rows if str(row.get("id")) not in previous.get(name, set())]
        for name, rows in after.items()
    }


def response_text(value: Any, *, _depth: int = 0) -> str:
    if _depth > 8:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "result", "message", "output"):
            text = response_text(value.get(key), _depth=_depth + 1)
            if text:
                return text
        return ""
    if isinstance(value, list):
        return "\n".join(
            filter(
                None,
                (response_text(item, _depth=_depth + 1) for item in value),
            )
        )
    return ""


def evidence_summary(
    delta: dict[str, list[dict[str, Any]]],
    host: str,
    *,
    expected_query_hash: str,
) -> dict[str, Any]:
    facade = _facade()
    routing = [
        row for row in delta.get("routing", []) if row.get("query_hash") == expected_query_hash
    ]
    finalizations = [row for row in delta.get("finalizations", []) if row.get("host") == host]
    receipts = [row for row in delta.get("receipts", []) if row.get("host") == host]
    route_traces = {str(row.get("trace_id")) for row in routing if row.get("trace_id")}
    final_traces = {str(row.get("trace_id")) for row in finalizations if row.get("trace_id")}
    receipt_traces = {str(row.get("trace_id")) for row in receipts if row.get("trace_id")}
    correlated = sorted(route_traces & final_traces)
    receipt_correlated = sorted(set(correlated) & receipt_traces)
    receipt_required = host in facade.RECEIPT_CAPABLE_HOSTS
    return {
        "new_ids": {
            name: [str(row.get("id")) for row in rows if row.get("id")]
            for name, rows in delta.items()
        },
        "counts": {name: len(rows) for name, rows in delta.items()},
        "host_finalization_count": len(finalizations),
        "host_receipt_count": len(receipts),
        "correlated_trace_ids": correlated,
        "receipt_correlated_trace_ids": receipt_correlated,
        "receipt_required": receipt_required,
        "receipt_proven": bool(receipt_correlated),
        "query_hash": expected_query_hash,
    }


@dataclass(frozen=True)
class ReadinessAssessment:
    native: dict[str, Any]
    control: dict[str, Any]
    profile_scope: str
    platform: dict[str, str]
    unmet: tuple[str, ...]


@dataclass(frozen=True)
class LivePreparation:
    store: Any | None
    before: dict[str, list[dict[str, Any]]] | None
    backend: Any | None
    prompt: str | None
    expected_query_hash: str | None
    error: str | None = None


@dataclass(frozen=True)
class InvocationOutcome:
    result: dict[str, Any] | None
    evidence: dict[str, Any] | None
    error: str | None = None


@dataclass(frozen=True)
class CanaryProof:
    invocation: dict[str, Any]
    result_scope: str
    passed: bool
    failures: tuple[str, ...]


def assess_readiness(
    host: str,
    path: Path,
    inspector: Callable[[str], dict[str, Any]],
) -> ReadinessAssessment:
    facade = _facade()
    try:
        inspected = inspector(host)
    except Exception:
        inspected = None
    native = (
        inspected
        if isinstance(inspected, dict)
        else {"host": host, "inspection_error": "native inspection unavailable"}
    )
    control = facade._read_control_without_writes(path, host)
    profile_scope = (
        "isolated-profile" if host in facade.ISOLATED_CANARY_HOSTS else "current-profile"
    )
    unmet: list[str] = []
    if native.get("executable_discovered") is not True:
        unmet.append("host executable not discovered")
    if host not in facade.ISOLATED_CANARY_HOSTS:
        if native.get("registered") is not True:
            unmet.append("Agency Runtime plugin registration not proven")
        if native.get("enabled") is not True:
            unmet.append("native plugin enablement not proven")
    if not native.get("host_version"):
        unmet.append("native host version not proven")
    if not native.get("install_id") or not native.get("bundle_digest"):
        unmet.append("managed bundle identity not proven")
    if host not in facade.SAFE_CANARY_HOSTS:
        unmet.append("host has no proven read-only, no-tools noninteractive canary mode")
    if control.get("enabled") is not True:
        unmet.append("Agency Runtime soft control is disabled or unverified")
    return ReadinessAssessment(
        native=native,
        control=control,
        profile_scope=profile_scope,
        platform={
            "system": facade.platform.system(),
            "release": facade.platform.release(),
            "machine": facade.platform.machine(),
        },
        unmet=tuple(unmet),
    )


def readiness_report(host: str, assessment: ReadinessAssessment) -> dict[str, Any]:
    return {
        "schema_version": "agency.host_canary.v1",
        "sampled_at": _facade()._utc_now(),
        "host": host,
        "profile_scope": assessment.profile_scope,
        "platform": assessment.platform,
        "native": assessment.native,
        "real_profile_native": assessment.native,
        "runtime_control": assessment.control,
        "ready": not assessment.unmet,
        "execute_confirmation": f"RUN LIVE {host} CANARY",
        "live_attempted": False,
        "canary_passed": False,
        "unmet_prerequisites": list(assessment.unmet),
    }


def prepare_live_invocation(
    host: str,
    *,
    path: Path,
    timeout: float,
    native: Mapping[str, Any],
    backend_factory: Callable[..., Any],
) -> LivePreparation:
    facade = _facade()
    try:
        store = facade.Store(path)
        before = store.recent_runtime_activity(limit=200)
    except Exception:
        return LivePreparation(
            store=None,
            before=None,
            backend=None,
            prompt=None,
            expected_query_hash=None,
            error="runtime evidence store is unavailable",
        )
    nonce = facade.secrets.token_hex(16)
    prompt = f"{facade.CANARY_PROMPT}\n\nCanary nonce: {nonce}"
    expected_query_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    try:
        if backend_factory is facade._backend:
            backend = backend_factory(
                host,
                db_path=path,
                timeout=timeout,
                native=native,
            )
        else:
            backend = backend_factory(host, db_path=path, timeout=timeout)
    except Exception:
        return LivePreparation(
            store=store,
            before=before,
            backend=None,
            prompt=prompt,
            expected_query_hash=expected_query_hash,
            error="safe noninteractive canary backend is unavailable",
        )
    return LivePreparation(
        store=store,
        before=before,
        backend=backend,
        prompt=prompt,
        expected_query_hash=expected_query_hash,
    )


def invoke_and_collect_evidence(
    preparation: LivePreparation,
    *,
    host: str,
    path: Path,
    prompt: str,
    expected_query_hash: str,
) -> InvocationOutcome:
    assert preparation.backend is not None
    assert preparation.store is not None
    assert preparation.before is not None
    try:
        with tempfile.TemporaryDirectory(
            prefix="canary-",
            dir=str(path.parent),
        ) as workdir:
            result = preparation.backend.execute(
                task=prompt,
                workdir=workdir,
                check=False,
            )
            if not isinstance(result, dict):
                raise RuntimeError("canary backend returned an invalid result")
    except Exception:
        return InvocationOutcome(
            result=None,
            evidence=None,
            error="safe host invocation failed before evidence could be evaluated",
        )
    try:
        after = preparation.store.recent_runtime_activity(limit=200)
    except Exception:
        return InvocationOutcome(
            result=None,
            evidence=None,
            error="runtime evidence could not be read after host invocation",
        )
    facade = _facade()
    return InvocationOutcome(
        result=result,
        evidence=facade._evidence_summary(
            facade._evidence_delta(preparation.before, after),
            host,
            expected_query_hash=expected_query_hash,
        ),
    )


def profile_is_proven(
    host: str,
    result_scope: str,
    isolated_plugin: dict[str, Any] | None,
    *,
    plugin_invoked: bool,
) -> bool:
    if result_scope == "current-profile":
        return True
    if result_scope != "isolated-profile" or isolated_plugin is None:
        return False
    if host == "codex":
        return isolated_plugin.get("registered") is True and isolated_plugin.get("enabled") is True
    return bool(
        host == "claude" and isolated_plugin.get("load_requested") is True and plugin_invoked
    )


def render_isolated_plugin(
    host: str,
    isolated_plugin: dict[str, Any] | None,
    *,
    plugin_invoked: bool,
) -> dict[str, Any] | None:
    rendered = dict(isolated_plugin) if isolated_plugin is not None else None
    if host == "claude" and rendered is not None:
        rendered["loaded"] = True if plugin_invoked else None
        rendered["invoked"] = True if plugin_invoked else None
    return rendered


def proof_failures(
    *,
    process_ok: bool,
    profile_proven: bool,
    header_valid: bool,
    evidence: Mapping[str, Any],
) -> tuple[str, ...]:
    failures: list[str] = []
    if not process_ok:
        failures.append("host invocation did not complete successfully")
    if not profile_proven:
        failures.append("canary profile plugin registration and enablement were not proven")
    if not header_valid:
        failures.append("final response header was not proven")
    if not evidence["correlated_trace_ids"]:
        failures.append("correlated routing and finalization evidence was not proven")
    elif evidence["receipt_required"] and not evidence["receipt_proven"]:
        failures.append(
            "the host exposes response telemetry but a correlated receipt was not proven"
        )
    return tuple(failures)


def evaluate_proof(
    host: str,
    *,
    result: dict[str, Any],
    evidence: dict[str, Any],
    default_profile_scope: str,
) -> CanaryProof:
    from agency_runtime.core.header.contract import validate_header

    facade = _facade()
    response = facade._response_text(result.get("output"))
    header_valid, header_missing = validate_header(response)
    process_ok = result.get("status") == "completed" and result.get("exit_code") == 0
    result_scope = str(result.get("profile_scope") or default_profile_scope)
    isolated_plugin = (
        result.get("isolated_plugin") if isinstance(result.get("isolated_plugin"), dict) else None
    )
    plugin_invoked = bool(evidence["correlated_trace_ids"])
    profile_proven = facade._profile_is_proven(
        host,
        result_scope,
        isolated_plugin,
        plugin_invoked=plugin_invoked,
    )
    evidence_passed = bool(
        evidence["correlated_trace_ids"]
        and (not evidence["receipt_required"] or evidence["receipt_proven"])
    )
    return CanaryProof(
        invocation={
            "backend": result.get("backend", host),
            "status": result.get("status"),
            "exit_code": result.get("exit_code"),
            "timed_out": result.get("status") == "timed_out",
            "stdout_truncated": bool(result.get("stdout_truncated")),
            "stderr_truncated": bool(result.get("stderr_truncated")),
            "header_valid": header_valid,
            "header_missing": header_missing,
            "profile_scope": result_scope,
            "isolated_plugin": facade._render_isolated_plugin(
                host,
                isolated_plugin,
                plugin_invoked=plugin_invoked,
            ),
        },
        result_scope=result_scope,
        passed=bool(process_ok and header_valid and evidence_passed and profile_proven),
        failures=facade._proof_failures(
            process_ok=process_ok,
            profile_proven=profile_proven,
            header_valid=header_valid,
            evidence=evidence,
        ),
    )


def attestation_payload(
    host: str,
    *,
    proof: CanaryProof,
    evidence: Mapping[str, Any],
    assessment: ReadinessAssessment,
    passed_at: str,
) -> dict[str, Any]:
    return {
        "host": host,
        "profile_scope": proof.result_scope,
        "platform_system": assessment.platform["system"],
        "platform_release": assessment.platform["release"],
        "platform_machine": assessment.platform["machine"],
        "host_version": str(assessment.native["host_version"]),
        "plugin_version": _facade().PLUGIN_VERSION,
        "install_id": str(assessment.native["install_id"]),
        "bundle_digest": str(assessment.native["bundle_digest"]),
        "trace_id": evidence["correlated_trace_ids"][0],
        "passed_at": passed_at,
    }


def attestation_identity_is_current(
    before: ReadinessAssessment,
    after: ReadinessAssessment,
) -> bool:
    """Require stable attested lineage across the complete live invocation."""
    if (
        after.unmet
        or before.profile_scope != after.profile_scope
        or before.platform != after.platform
    ):
        return False
    fields = ("host_version", "install_id", "bundle_digest")
    return all(
        str(before.native.get(field) or "") == str(after.native.get(field) or "")
        for field in fields
    )


def persist_attestation(
    store: Any,
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        attestation = store.record_host_canary_attestation(**payload)
    except Exception:
        return None, "successful canary evidence could not be durably attested"
    return attestation, None


__all__ = [
    "CanaryProof",
    "InvocationOutcome",
    "LivePreparation",
    "ReadinessAssessment",
    "assess_readiness",
    "attestation_identity_is_current",
    "attestation_payload",
    "evaluate_proof",
    "evidence_delta",
    "evidence_summary",
    "ids",
    "invoke_and_collect_evidence",
    "persist_attestation",
    "prepare_live_invocation",
    "profile_is_proven",
    "proof_failures",
    "readiness_report",
    "render_isolated_plugin",
    "response_text",
]
