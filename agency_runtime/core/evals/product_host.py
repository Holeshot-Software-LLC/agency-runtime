"""Credential-isolated native-host execution for one-shot product trials."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import stat
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Final

from agency_runtime.core import canary
from agency_runtime.core.bounded_io import FileSizeLimitError, read_bounded_regular_file
from agency_runtime.core.canary_backends import SafeCodexCanaryBackend
from agency_runtime.core.delegation.backends import run_bounded_process
from agency_runtime.core.evals.product_one_shot import ProductHostExecution
from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point
from agency_runtime.core.installer import inspect_host_installation
from agency_runtime.core.store.sqlite import Store, _default_db_path

CODEX_PRODUCT_DEVELOPER_INSTRUCTIONS: Final[str] = (
    "This is a bounded Agency Runtime product evaluation. If the current task contains "
    "[AGENCY EXACT TASK EXECUTION v1], you are an activated specialist child: execute the "
    "exact hash-bound work-unit goal included in this current execution turn under the "
    "already activated specialist instructions. Use permitted workspace tools for every required "
    "implementation or documentation change. When that goal contains the product harness "
    "workspace-write proof, read its terminal `mutation_scope` field before working. A "
    "`workspace_write` child must check the named proof file before any other workspace "
    "mutation, create it with the exact supplied line when absent, and leave an existing "
    "proof unchanged. Verify the requested evidence before returning. Do not call "
    "spawn_agent, wait_agent, or followup_task, do not delegate further, and return one "
    "bounded evidence-backed result. If the current task contains "
    "[AGENCY EXACT SPECIALIST ACTIVATION v1] or "
    "[AGENCY EXACT SPECIALIST ACTIVATION v2], you are a delegated specialist child: "
    "this first turn only activates the exact goal and specialist. Perform no product work, "
    "use no tools, and return one bounded readiness acknowledgement. "
    "Otherwise, when the current task contains [AGENCY DELEGATION PLAN], you are the "
    "non-working parent scheduler and the user has authorized native delegation for every "
    "accepted persisted plan row. Respect each row's depends_on field. Schedule every row "
    "exactly once, with no retries, one child at a time. For each dependency-ready row call "
    "spawn_agent with fork_turns set to none, task_name set to "
    "that row's exact native_task_name, and message set to that row's exact decoded goal. "
    "Call wait_agent once with timeout_ms=60000 for its activation-only turn. If that "
    "wait times out or does not report the exact child completed, stop without sending "
    "the execution followup or scheduling another row. Then call followup_task exactly "
    "once on the exact canonical task path returned by spawn_agent. Set message to the "
    "exact concatenation of the row's JSON-decoded execution_message_prefix and the same "
    "exact decoded goal sent to spawn_agent, with no separator. For that execution turn, "
    "call wait_agent with timeout_ms=120000. A nonterminal commentary update is not "
    "completion: repeat that same wait up to two additional times until the exact child "
    "reports completed. If a wait times out, the child fails, or the third execution wait "
    "remains nonterminal, stop without scheduling another row. Never spawn the next row until "
    "the exact prior child execution is terminal. Use no "
    "non-collaboration tools and perform no product work in the parent. "
    "Do not merge, omit, broaden, decline, or duplicate an accepted row. After every child "
    "finishes, consolidate only their reported outcomes and return the required Agency "
    "header and bounded product result. If the task contains neither marker, follow the "
    "ordinary native host policy without claiming Agency specialist execution."
)

_CODEX_PRODUCT_EXEC_PREFIX: Final[tuple[str, ...]] = (
    "--json",
    "--color",
    "never",
    "--ignore-rules",
    "--strict-config",
    "--enable",
    "multi_agent_v2",
    "--sandbox",
    "workspace-write",
    "-c",
    'web_search="disabled"',
    "-c",
    "apps._default.enabled=false",
    "-c",
    "mcp_servers={}",
    "-c",
    "agents.enabled=true",
)
_CODEX_PRODUCT_EXEC_SUFFIX: Final[tuple[str, ...]] = (
    "--skip-git-repo-check",
    "--dangerously-bypass-hook-trust",
    "-",
)
CODEX_PRODUCT_EXEC_OPTIONS: Final[tuple[str, ...]] = (
    *_CODEX_PRODUCT_EXEC_PREFIX,
    "-c",
    f"developer_instructions={json.dumps(CODEX_PRODUCT_DEVELOPER_INSTRUCTIONS)}",
    *_CODEX_PRODUCT_EXEC_SUFFIX,
)
_CODEX_NATIVE_ONLY_PRODUCT_EXEC_OPTIONS: Final[tuple[str, ...]] = (
    *_CODEX_PRODUCT_EXEC_PREFIX,
    *_CODEX_PRODUCT_EXEC_SUFFIX,
)
PROVEN_PRODUCT_HOSTS: Final[frozenset[str]] = frozenset({"codex"})
_MAX_RESPONSE_SUMMARY_CHARS: Final[int] = 256
_WORKSPACE_WRITE_PROOF_FILE: Final[str] = ".agency-runtime-workspace-write-proof"
_WORKSPACE_WRITE_PROOF_PREFIX: Final[str] = "agency-runtime-product-write-proof:"
_WORKSPACE_WRITE_PROOF_SCHEMA: Final[str] = "agency.product-workspace-write-proof.v1"
_WORKSPACE_TRUST_SCHEMA: Final[str] = "agency.codex-isolated-workspace-trust.v1"
_HOOK_TRUST_SCHEMA: Final[str] = "agency.codex-hook-trust-mode.v1"


def _codex_options(model: str, *, agency_mode: bool = True) -> tuple[str, ...]:
    base_options = (
        CODEX_PRODUCT_EXEC_OPTIONS if agency_mode else _CODEX_NATIVE_ONLY_PRODUCT_EXEC_OPTIONS
    )
    normalized = str(model or "").strip()
    if not normalized:
        return base_options
    if len(normalized) > 256 or any(character.isspace() for character in normalized):
        raise ValueError("model is invalid")
    return (*base_options[:-1], "--model", normalized, "-")


def _expected_prompt_hash(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _duration_ms(started: float) -> float:
    value = (time.monotonic() - started) * 1000
    return round(value, 3) if math.isfinite(value) and value >= 0 else 0.0


def _safe_error(prefix: str, exc: BaseException) -> str:
    return f"{prefix}: {type(exc).__name__}"[:_MAX_RESPONSE_SUMMARY_CHARS]


def _prompt_with_workspace_write_proof(prompt: str, prompt_hash: str) -> tuple[str, str]:
    token = _WORKSPACE_WRITE_PROOF_PREFIX + prompt_hash.removeprefix("sha256:")
    wrapped = (
        "[AGENCY PRODUCT HARNESS WORKSPACE-WRITE PROOF]\n"
        "Read the terminal `mutation_scope` field in this exact work-unit goal. A delegated "
        "child with `mutation_scope=workspace_write` must check the relative file below "
        "before any other workspace mutation. If it is absent, create it as that child's "
        "first mutation with the exact single line below. If it already exists, leave it "
        "unchanged. Read-only children and the non-working parent must not create it. File: "
        f"`{_WORKSPACE_WRITE_PROOF_FILE}` containing this single line exactly:\n"
        f"{token}\n"
        "Leave that file in place for the harness. It is evidence only, not a product "
        "artifact. Continue with the complete product request after the delegated "
        "workspace-write child creates it.\n"
        "[END AGENCY PRODUCT HARNESS WORKSPACE-WRITE PROOF]\n\n"
        f"{prompt}"
    )
    return wrapped, token


def _prepare_workspace(workspace: Path) -> Path:
    try:
        resolved = workspace.expanduser().resolve(strict=True)
        metadata = os.lstat(resolved)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("product workspace is unavailable") from exc
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("product workspace must be a real directory")
    proof = resolved / _WORKSPACE_WRITE_PROOF_FILE
    try:
        os.lstat(proof)
    except FileNotFoundError:
        return resolved
    except OSError as exc:
        raise ValueError("product workspace write proof cannot be inspected") from exc
    raise ValueError("product workspace write proof must not preexist execution")


def _workspace_identity(workspace: Path) -> str:
    normalized = str(workspace)
    if os.name == "nt":
        normalized = normalized.casefold()
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _workspace_trust_evidence(
    result: Mapping[str, Any],
    *,
    workspace: Path,
) -> dict[str, Any]:
    expected_hash = _workspace_identity(workspace)
    candidate = result.get("workspace_trust")
    proven = bool(
        isinstance(candidate, Mapping)
        and candidate.get("schema") == _WORKSPACE_TRUST_SCHEMA
        and candidate.get("status") == "trusted"
        and candidate.get("scope") == "exact-workspace"
        and candidate.get("workspace_hash") == expected_hash
        and candidate.get("persistent_profile_changed") is False
    )
    return {
        "schema": _WORKSPACE_TRUST_SCHEMA,
        "proven": proven,
        "status": "trusted" if proven else "unproven",
        "scope": "exact-workspace",
        "workspace_hash": expected_hash,
        "persistent_profile_changed": False if proven else None,
        "reason": (
            "exact_isolated_profile_projection"
            if proven
            else "workspace_trust_evidence_missing_or_mismatched"
        ),
    }


def _workspace_write_evidence(workspace: Path, *, expected_token: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": _WORKSPACE_WRITE_PROOF_SCHEMA,
        "proven": False,
        "relative_path": _WORKSPACE_WRITE_PROOF_FILE,
        "reason": "proof_file_missing",
        "removed_after_verification": False,
    }
    candidate = workspace / _WORKSPACE_WRITE_PROOF_FILE
    try:
        metadata = os.lstat(candidate)
    except FileNotFoundError:
        return evidence
    except OSError:
        evidence["reason"] = "proof_file_unavailable"
        return evidence
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
        evidence["reason"] = "proof_file_unsafe"
        return evidence
    try:
        payload = read_bounded_regular_file(
            candidate,
            limit=512,
            label="product workspace-write proof",
        )
    except FileSizeLimitError:
        evidence["reason"] = "proof_file_oversized"
        return evidence
    except OSError:
        evidence["reason"] = "proof_file_unavailable"
        return evidence
    try:
        content = payload.decode("utf-8")
    except UnicodeDecodeError:
        evidence["reason"] = "proof_file_invalid"
        return evidence
    if content not in {expected_token, expected_token + "\n", expected_token + "\r\n"}:
        evidence["reason"] = "proof_file_content_mismatch"
        return evidence
    try:
        candidate.unlink()
    except OSError:
        evidence["reason"] = "proof_file_cleanup_failed"
        return evidence
    if candidate.exists():
        evidence["reason"] = "proof_file_cleanup_failed"
        return evidence
    evidence.update(
        proven=True,
        reason="exact_model_write_observed",
        removed_after_verification=True,
    )
    return evidence


def _hook_trust_evidence(result: Mapping[str, Any]) -> dict[str, Any]:
    """Project the explicit one-invocation bypass without calling it trust."""

    proven = bool(
        result.get("trust_mode") == "autonomous_bypass"
        and result.get("trust_bypass_used") is True
        and result.get("persistent_trust_changed") is False
    )
    return {
        "schema": _HOOK_TRUST_SCHEMA,
        "proven": proven,
        "trust_mode": "autonomous_bypass" if proven else "unproven",
        "status": "bypassed" if proven else "unproven",
        "persistent_trust_changed": False if proven else None,
    }


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
        workspace_write_proven=False,
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
    workspace: Path,
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
        exec_options=_codex_options(model, agency_mode=master_enabled),
        require_existing_store=True,
        require_exact_activation_rollout=True,
        rollout_contract="product",
        hook_event_diagnostics=master_enabled,
        trusted_workdir=str(workspace.resolve(strict=True)),
        trust_mode="autonomous_bypass",
        project_agency_global_guidance=True,
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
    executed_prompt, write_proof_token = _prompt_with_workspace_write_proof(prompt, prompt_hash)
    executed_prompt_hash = _expected_prompt_hash(executed_prompt)

    path = Path(db_path).expanduser() if db_path else _default_db_path()
    try:
        resolved_workspace = _prepare_workspace(workspace)
        native = dict(inspector(normalized_host))
        store = Store(path)
        before = (
            None
            if normalized_host == "codex" and normalized_mode == "agency"
            else store.recent_runtime_activity(limit=500)
        )
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
            workspace=resolved_workspace,
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
        result = backend.execute(
            task=executed_prompt,
            workdir=str(resolved_workspace),
            check=False,
        )
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
        write_evidence = _workspace_write_evidence(
            resolved_workspace,
            expected_token=write_proof_token,
        )
        trust_evidence = _workspace_trust_evidence(
            result,
            workspace=resolved_workspace,
        )
        hook_trust_evidence = _hook_trust_evidence(result)
        if normalized_host == "codex" and normalized_mode == "agency":
            evidence = store.get_canary_activation_snapshot(
                host=normalized_host,
                query_hash=executed_prompt_hash.removeprefix("sha256:"),
            )
        else:
            after = store.recent_runtime_activity(limit=500)
            delta = canary._evidence_delta(before, after)
            evidence = canary._evidence_summary(
                delta,
                normalized_host,
                expected_query_hash=executed_prompt_hash.removeprefix("sha256:"),
            )
        proof = canary._evaluate_proof(
            normalized_host,
            result=result,
            evidence=evidence,
            default_profile_scope="isolated-profile",
            mode=normalized_mode,
            activation_contract="product",
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
    if trust_evidence.get("proven") is not True:
        failures = (*failures, "workspace_trust_not_proven")
    if hook_trust_evidence.get("proven") is not True:
        failures = (*failures, "hook_trust_bypass_not_proven")
    if write_evidence.get("proven") is not True:
        failures = (*failures, "workspace_write_not_proven")
    return ProductHostExecution(
        host=normalized_host,
        mode=normalized_mode,
        status=str(result.get("status") or "failed"),
        exit_code=int(result.get("exit_code") or 0),
        duration_ms=_duration_ms(started),
        profile_scope=proof.result_scope,
        runtime_contract_passed=bool(
            proof.passed
            and trust_evidence.get("proven") is True
            and hook_trust_evidence.get("proven") is True
            and write_evidence.get("proven") is True
        ),
        agency_evidence={
            "mode": normalized_mode,
            "proof": proof.invocation,
            "runtime": evidence,
            "workspace_trust": trust_evidence,
            "hook_trust": hook_trust_evidence,
            "workspace_write": write_evidence,
            "product_prompt_hash": prompt_hash,
            "executed_prompt_hash": executed_prompt_hash,
            "failures": list(failures),
        },
        requested_model=requested_model,
        actual_model=str(
            (
                proof.invocation.get("header", {})
                if isinstance(proof.invocation.get("header"), Mapping)
                else {}
            ).get("actual_model_selected", "")
        ),
        router="",
        response_summary=response_summary,
        error="; ".join(failures)[:_MAX_RESPONSE_SUMMARY_CHARS],
        workspace_write_proven=write_evidence.get("proven") is True,
    )


__all__ = [
    "CODEX_PRODUCT_DEVELOPER_INSTRUCTIONS",
    "CODEX_PRODUCT_EXEC_OPTIONS",
    "PROVEN_PRODUCT_HOSTS",
    "execute_product_host",
]
