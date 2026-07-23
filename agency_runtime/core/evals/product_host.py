"""Credential-isolated native-host execution for one-shot product trials."""

from __future__ import annotations

import hashlib
import math
import os
import shutil
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Final

from agency_runtime.core import canary
from agency_runtime.core.canary_backends import SafeCodexCanaryBackend
from agency_runtime.core.delegation.backends import run_bounded_process
from agency_runtime.core.evals.product_one_shot import ProductHostExecution
from agency_runtime.core.installer import inspect_host_installation
from agency_runtime.core.store.sqlite import Store, _default_db_path

CODEX_PRODUCT_EXEC_OPTIONS: Final[tuple[str, ...]] = (
    "--json",
    "--color",
    "never",
    "--ephemeral",
    "--ignore-rules",
    "--strict-config",
    "--sandbox",
    "workspace-write",
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
PROVEN_PRODUCT_HOSTS: Final[frozenset[str]] = frozenset({"codex"})
_MAX_RESPONSE_SUMMARY_CHARS: Final[int] = 256


def _codex_options(model: str) -> tuple[str, ...]:
    normalized = str(model or "").strip()
    if not normalized:
        return CODEX_PRODUCT_EXEC_OPTIONS
    if len(normalized) > 256 or any(character.isspace() for character in normalized):
        raise ValueError("model is invalid")
    return (*CODEX_PRODUCT_EXEC_OPTIONS[:-1], "--model", normalized, "-")


def _expected_prompt_hash(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _duration_ms(started: float) -> float:
    value = (time.monotonic() - started) * 1000
    return round(value, 3) if math.isfinite(value) and value >= 0 else 0.0


def _safe_error(prefix: str, exc: BaseException) -> str:
    return f"{prefix}: {type(exc).__name__}"[:_MAX_RESPONSE_SUMMARY_CHARS]


def _failed_execution(
    *,
    host: str,
    mode: str,
    started: float,
    model: str,
    error: str,
) -> ProductHostExecution:
    return ProductHostExecution(
        host=host,
        mode=mode,
        status="failed",
        exit_code=1,
        duration_ms=_duration_ms(started),
        profile_scope="isolated-profile",
        runtime_contract_passed=False,
        agency_evidence={},
        requested_model=model,
        actual_model="",
        router="",
        response_summary="",
        error=error[:_MAX_RESPONSE_SUMMARY_CHARS],
    )


def _default_inspector(host: str) -> dict[str, Any]:
    return inspect_host_installation(host)


def _codex_product_backend(
    *,
    native: Mapping[str, Any],
    db_path: Path,
    timeout: float,
    master_enabled: bool,
    model: str,
    resolver: Callable[[str], str | None],
    runner: Callable[..., Any] | None,
    environ: Mapping[str, str],
) -> SafeCodexCanaryBackend:
    """Build the product backend without inheriting the shorter canary deadline."""

    executable = resolver("codex")
    if not executable:
        raise ValueError("Codex executable is unavailable")
    source_home = canary._source_home(environ)
    original_home = Path(environ.get("CODEX_HOME") or (source_home / ".codex")).expanduser()
    return SafeCodexCanaryBackend(
        executable=executable,
        db_path=db_path,
        timeout=timeout,
        marketplace=canary._codex_marketplace(native),
        auth_source=original_home / "auth.json",
        process_runner=runner or run_bounded_process,
        source_env=environ,
        master_enabled=master_enabled,
        profile_scope="isolated-profile",
        exec_options=_codex_options(model),
    )


def execute_product_host(
    *,
    prompt: str,
    prompt_hash: str,
    host: str,
    mode: str,
    workspace: Path,
    timeout: float,
    model: str = "",
    db_path: str | Path | None = None,
    inspector: Callable[[str], Mapping[str, Any]] = _default_inspector,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> ProductHostExecution:
    """Run one native host in an isolated profile and reconcile runtime evidence."""

    started = time.monotonic()
    normalized_host = str(host or "").strip().casefold()
    normalized_mode = str(mode or "").strip().casefold()
    requested_model = str(model or "").strip()
    if normalized_host not in PROVEN_PRODUCT_HOSTS:
        raise ValueError(
            f"{normalized_host or 'unknown'} has no proven isolated workspace-write product backend"
        )
    if normalized_mode not in canary.CANARY_MODES:
        raise ValueError(f"unsupported product trial mode: {normalized_mode}")
    if prompt_hash != _expected_prompt_hash(prompt):
        raise ValueError("product prompt hash does not match the executed prompt")

    path = Path(db_path).expanduser() if db_path else _default_db_path()
    try:
        native = dict(inspector(normalized_host))
        store = Store(path)
        before = store.recent_runtime_activity(limit=500)
        source_environment = os.environ if environ is None else environ
        backend = _codex_product_backend(
            native=native,
            db_path=path,
            timeout=timeout,
            resolver=resolver,
            runner=runner,
            master_enabled=normalized_mode == "agency",
            model=requested_model,
            environ=source_environment,
        )
    except Exception as exc:
        return _failed_execution(
            host=normalized_host,
            mode=normalized_mode,
            started=started,
            model=requested_model,
            error=_safe_error("safe product backend preparation failed", exc),
        )

    try:
        result = backend.execute(task=prompt, workdir=str(workspace), check=False)
        if not isinstance(result, dict):
            raise TypeError("host result is not a mapping")
    except Exception as exc:
        return _failed_execution(
            host=normalized_host,
            mode=normalized_mode,
            started=started,
            model=requested_model,
            error=_safe_error("safe product host invocation failed", exc),
        )

    try:
        after = store.recent_runtime_activity(limit=500)
        delta = canary._evidence_delta(before, after)
        evidence = canary._evidence_summary(
            delta,
            normalized_host,
            expected_query_hash=prompt_hash.removeprefix("sha256:"),
        )
        proof = canary._evaluate_proof(
            normalized_host,
            result=result,
            evidence=evidence,
            default_profile_scope="isolated-profile",
            mode=normalized_mode,
        )
    except Exception as exc:
        return _failed_execution(
            host=normalized_host,
            mode=normalized_mode,
            started=started,
            model=requested_model,
            error=_safe_error("runtime evidence reconciliation failed", exc),
        )

    response = canary._response_text(result.get("output"))
    response_summary = (
        f"nonempty response captured ({len(response)} characters)" if response.strip() else ""
    )
    failures = tuple(str(item) for item in proof.failures)
    return ProductHostExecution(
        host=normalized_host,
        mode=normalized_mode,
        status=str(result.get("status") or "failed"),
        exit_code=int(result.get("exit_code") or 0),
        duration_ms=_duration_ms(started),
        profile_scope=proof.result_scope,
        runtime_contract_passed=proof.passed,
        agency_evidence={
            "mode": normalized_mode,
            "proof": proof.invocation,
            "runtime": evidence,
            "failures": list(failures),
        },
        requested_model=requested_model,
        actual_model="",
        router="",
        response_summary=response_summary,
        error="; ".join(failures)[:_MAX_RESPONSE_SUMMARY_CHARS],
    )


__all__ = [
    "CODEX_PRODUCT_EXEC_OPTIONS",
    "PROVEN_PRODUCT_HOSTS",
    "execute_product_host",
]
