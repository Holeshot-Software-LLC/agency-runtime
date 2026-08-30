"""Explicitly confirmed Claude proof for one accepted producer/verifier outcome."""

from __future__ import annotations

import logging
import re
import secrets
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from agency_runtime.core import canary
from agency_runtime.core.accepted_outcome_canary_contract import (
    ACCEPTED_OUTCOME_CONFIRMATION,
    ACCEPTED_OUTCOME_CONTRACTOR_SLUG,
    build_accepted_outcome_canary_prompt,
)
from agency_runtime.core.child_delivery_evidence import (
    _accepted_outcome_result_is_valid,
    _HostAcceptedOutcomeCollection,
)
from agency_runtime.core.private_paths import private_temporary_directory

logger = logging.getLogger(__name__)

_SCHEMA = "agency.accepted_outcome_canary.v1"
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _bounded_identity(value: object, *, maximum: int = 256) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    return value


def _requested_provider(backend: object) -> str | None:
    return _bounded_identity(getattr(backend, "child_judge_provider", None), maximum=128)


def _requested_parent_recruiter_provider(backend: object) -> str | None:
    return _bounded_identity(getattr(backend, "parent_recruiter_provider", None), maximum=128)


def _safe_invocation(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project process facts only; model and child text never enter the report."""

    projected = {
        "backend": record.get("backend"),
        "profile_scope": record.get("profile_scope"),
        "status": record.get("status"),
        "exit_code": record.get("exit_code"),
        "timed_out": record.get("status") == "timed_out",
        "stdout_truncated": record.get("stdout_truncated") is True,
        "stderr_truncated": record.get("stderr_truncated") is True,
        "host_accepted_outcome_reason": record.get("host_accepted_outcome_reason"),
    }
    requested = _bounded_identity(record.get("child_judge_provider_requested"), maximum=128)
    if requested is not None:
        projected["child_judge_provider_requested"] = requested
    parent_requested = _bounded_identity(
        record.get("parent_recruiter_provider_requested"), maximum=128
    )
    if parent_requested is not None:
        projected["parent_recruiter_provider_requested"] = parent_requested
    failure = _bounded_identity(record.get("failure_reason"), maximum=128)
    if failure is not None:
        projected["failure_reason"] = failure
    return projected


def _applied_provider(route: Mapping[str, Any]) -> str | None:
    attempts = route.get("provider_attempts")
    if not isinstance(attempts, list):
        return None
    applied = [
        _bounded_identity(attempt.get("provider_name"), maximum=128)
        for attempt in attempts
        if isinstance(attempt, Mapping) and attempt.get("status") == "applied"
    ]
    return applied[0] if len(applied) == 1 and applied[0] is not None else None


def _card_projection(value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != {
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "body_character_length",
    }:
        return None
    slug = _bounded_identity(value.get("specialist_slug"), maximum=128)
    version = _bounded_identity(value.get("specialist_version"), maximum=128)
    prompt_hash = value.get("specialist_prompt_hash")
    body_length = value.get("body_character_length")
    if (
        slug is None
        or version is None
        or not isinstance(prompt_hash, str)
        or _LOWER_SHA256.fullmatch(prompt_hash) is None
        or isinstance(body_length, bool)
        or not isinstance(body_length, int)
        or body_length <= 0
    ):
        return None
    return {
        "specialist_slug": slug,
        "specialist_version": version,
        "specialist_prompt_hash": prompt_hash,
        "body_character_length": body_length,
    }


def _route_projection(
    store: object,
    *,
    decision_id: str,
    expected_provider: str,
) -> dict[str, Any] | None:
    get_route = getattr(store, "get_native_child_staffing_decision", None)
    get_delivery = getattr(store, "get_native_child_delivery_verification", None)
    if not callable(get_route) or not callable(get_delivery):
        return None
    route = get_route(decision_id)
    delivery = get_delivery(decision_id)
    if not isinstance(route, Mapping) or not isinstance(delivery, Mapping):
        return None
    binding_kind = _bounded_identity(route.get("binding_kind"), maximum=32)
    binding_id = _bounded_identity(route.get("binding_id"), maximum=512)
    launch_id = _bounded_identity(route.get("launch_id"), maximum=512)
    child_id = _bounded_identity(delivery.get("child_id"), maximum=512)
    provider = _applied_provider(route)
    receipt_digest = route.get("provider_receipt_digest")
    artifact_digest = delivery.get("artifact_digest")
    cards = route.get("cards")
    projected_cards = [_card_projection(card) for card in cards] if isinstance(cards, list) else []
    bindings_match = all(
        delivery.get(field) == route.get(field)
        for field in (
            "host",
            "parent_session_id",
            "parent_trace_id",
            "launch_id",
            "binding_kind",
            "binding_id",
            "nonce",
        )
    )
    binding_is_exact = (binding_kind == "child_id" and binding_id == child_id) or (
        binding_kind == "launch_id"
        and binding_id is not None
        and launch_id is not None
        and binding_id == launch_id
    )
    if (
        route.get("decision_id") != decision_id
        or delivery.get("decision_id") != decision_id
        or route.get("host") != "claude"
        or not binding_is_exact
        or child_id is None
        or delivery.get("verified_delivery") is not True
        or provider != expected_provider
        or not isinstance(receipt_digest, str)
        or _LOWER_SHA256.fullmatch(receipt_digest) is None
        or not isinstance(artifact_digest, str)
        or _LOWER_SHA256.fullmatch(artifact_digest) is None
        or not bindings_match
        or not projected_cards
        or any(card is None for card in projected_cards)
    ):
        return None
    return {
        "decision_id": decision_id,
        "parent_session_id": route["parent_session_id"],
        "parent_trace_id": route["parent_trace_id"],
        "child_id": child_id,
        "provider_answered": provider,
        "provider_receipt_digest": receipt_digest,
        "artifact_digest": artifact_digest,
        "cards": projected_cards,
    }


def _outcome_projection(collection: _HostAcceptedOutcomeCollection) -> dict[str, Any] | None:
    result = collection.result
    if not _accepted_outcome_result_is_valid(result) or not isinstance(result, Mapping):
        return None
    return {
        "reason": result["reason"],
        "recorded": result["recorded"],
        "promoted": result["promoted"],
        "event_id": result["event_id"],
        "worker_id": result["worker_id"],
        "accepted_outcome_key": result["accepted_outcome_key"],
        "artifact_digest": result["artifact_digest"],
    }


def _target_worker_is_ready(store: object) -> tuple[bool, dict[str, Any] | None]:
    getter = getattr(store, "get_workforce_worker", None)
    if not callable(getter):
        return False, None
    try:
        worker = getter(ACCEPTED_OUTCOME_CONTRACTOR_SLUG)
    except Exception:
        return False, None
    if (
        not isinstance(worker, Mapping)
        or worker.get("agent_slug") != ACCEPTED_OUTCOME_CONTRACTOR_SLUG
        or worker.get("enabled") is not True
        or worker.get("employment_class") not in {"contractor", "employee"}
        or _bounded_identity(worker.get("worker_id")) is None
    ):
        return False, None
    return True, {
        "worker_id": worker["worker_id"],
        "specialist_slug": worker["agent_slug"],
        "employment_class": worker["employment_class"],
    }


def _validate_request(
    host: str,
    *,
    mode: str,
    profile_scope: str,
    require_existing_store: bool,
) -> None:
    if host != "claude":
        raise ValueError("accepted-outcome canaries support Claude only")
    if mode != "agency":
        raise ValueError("accepted-outcome canaries require Agency mode")
    if profile_scope != "isolated-profile":
        raise ValueError("accepted-outcome canaries require an isolated profile")
    if require_existing_store:
        raise ValueError("accepted-outcome canaries do not support existing-store mode")


def run_accepted_outcome_canary(  # noqa: C901 - one bounded live-proof orchestration
    host: str,
    *,
    execute: bool = False,
    confirm: str = "",
    db_path: str | Path | None = None,
    timeout: float = 120,
    mode: str = "agency",
    profile_scope: str = "isolated-profile",
    require_existing_store: bool = False,
    inspector: Callable[[str], dict[str, Any]] = canary._default_inspector,
    backend_factory: Callable[..., Any] = canary._backend,
) -> dict[str, Any]:
    """Inspect readiness or record one exact host-evidenced Claude outcome."""

    if type(execute) is not bool or type(require_existing_store) is not bool:
        raise TypeError("accepted-outcome canary flags must be booleans")
    _validate_request(
        host,
        mode=mode,
        profile_scope=profile_scope,
        require_existing_store=require_existing_store,
    )
    timeout = canary._validated_timeout(timeout)
    path = Path(db_path).expanduser() if db_path else canary._default_db_path()
    assessment = canary._assess_readiness(host, path, inspector, profile_scope=profile_scope)
    report = canary._readiness_report(host, assessment, mode=mode)
    report.update(
        schema_version=_SCHEMA,
        canary_kind="accepted-outcome",
        execute_confirmation=ACCEPTED_OUTCOME_CONFIRMATION,
        promotion_observed=False,
    )
    master_before = canary._attach_master_readiness(report, mode=mode)
    if master_before is None or not execute:
        return report
    if confirm != ACCEPTED_OUTCOME_CONFIRMATION:
        report["unmet_prerequisites"].append(
            f"confirmation must exactly match: {ACCEPTED_OUTCOME_CONFIRMATION}"
        )
        return report
    if report["unmet_prerequisites"]:
        return report

    pair_id = secrets.token_hex(16)
    preparation = canary._prepare_live_invocation(
        host,
        path=path,
        timeout=timeout,
        native=assessment.native,
        backend_factory=backend_factory,
        master_enabled=True,
        mode="agency",
        profile_scope="isolated-profile",
        require_existing_store=False,
        base_prompt=build_accepted_outcome_canary_prompt(pair_id),
        require_accepted_outcome_parent_recruiter=True,
    )
    if preparation.error:
        report["unmet_prerequisites"].append(preparation.error)
        return report
    if preparation.store is None or preparation.backend is None or preparation.prompt is None:
        report["unmet_prerequisites"].append(
            "safe accepted-outcome preparation returned incomplete invocation state"
        )
        return report
    requested_provider = _requested_provider(preparation.backend)
    if requested_provider is None:
        report["unmet_prerequisites"].append(
            "accepted-outcome child judge provider pin is unavailable"
        )
        return report
    requested_parent_recruiter = _requested_parent_recruiter_provider(preparation.backend)
    if requested_parent_recruiter is None:
        report["unmet_prerequisites"].append(
            "accepted-outcome parent-recruiter provider pin is unavailable"
        )
        return report
    worker_ready, worker = _target_worker_is_ready(preparation.store)
    if not worker_ready or worker is None:
        report["unmet_prerequisites"].append(
            "accepted-outcome target workforce worker is unavailable or disabled"
        )
        return report
    report["target_worker"] = worker
    report["pair_id"] = pair_id
    report["child_judge_provider_requested"] = requested_provider
    report["parent_recruiter_provider_requested"] = requested_parent_recruiter
    report["live_attempted"] = True

    record: Mapping[str, Any] | None = None
    collection: _HostAcceptedOutcomeCollection | None = None
    try:
        execute_pair = getattr(preparation.backend, "execute_with_accepted_outcome", None)
        if not callable(execute_pair):
            raise TypeError("safe backend lacks accepted-outcome execution")
        with private_temporary_directory(prefix="accepted-outcome-canary") as workdir:
            candidate_record, candidate_collection = execute_pair(
                task=preparation.prompt,
                workdir=str(workdir),
                store=preparation.store,
                check=False,
            )
        if not isinstance(candidate_record, Mapping):
            raise TypeError("safe backend returned an invalid process record")
        record = candidate_record
        if type(candidate_collection) is _HostAcceptedOutcomeCollection:
            collection = candidate_collection
    except Exception:
        logger.debug("safe accepted-outcome invocation raised", exc_info=True)
        report["unmet_prerequisites"].append(
            "safe accepted-outcome invocation failed before evidence could be evaluated"
        )
        return report

    report["sampled_at"] = canary._utc_now()
    report["invocation"] = _safe_invocation(record)
    if not canary._master_control_is_unchanged(
        report,
        master_before,
        read_failure=("authoritative Agency master control could not be re-read after invocation"),
        drift_failure="Agency master control changed during the accepted-outcome invocation",
    ):
        return report
    current = canary._assess_readiness(host, path, inspector, profile_scope=profile_scope)
    if not canary._attestation_identity_is_current(assessment, current):
        report["unmet_prerequisites"].append(
            "native host or managed bundle identity changed during the accepted-outcome canary"
        )
        return report
    if (
        record.get("status") != "completed"
        or record.get("child_judge_provider_requested") != requested_provider
        or record.get("parent_recruiter_provider_requested") != requested_parent_recruiter
    ):
        report["unmet_prerequisites"].append(
            "safe Claude invocation did not complete with both requested provider pins"
        )
        return report
    if collection is None:
        reason = _bounded_identity(record.get("host_accepted_outcome_reason"), maximum=128)
        suffix = f" ({reason})" if reason is not None else ""
        report["unmet_prerequisites"].append(
            "verified Claude producer/verifier outcome was not collected" + suffix
        )
        return report
    if not collection.pair_id:
        report["unmet_prerequisites"].append(
            f"verified Claude producer/verifier outcome was not collected ({collection.reason})"
        )
        return report
    if collection.pair_id != pair_id:
        report["unmet_prerequisites"].append(
            "collected producer/verifier pair did not match the canary identity"
        )
        return report

    producer = _route_projection(
        preparation.store,
        decision_id=collection.producer_decision_id,
        expected_provider=requested_provider,
    )
    verifier = _route_projection(
        preparation.store,
        decision_id=collection.verifier_decision_id,
        expected_provider=requested_provider,
    )
    outcome = _outcome_projection(collection)
    if producer is None or verifier is None or outcome is None:
        report["unmet_prerequisites"].append(
            "accepted-outcome route, delivery, or Store result projection was invalid"
        )
        return report
    same_parent = (
        producer["parent_session_id"] == verifier["parent_session_id"]
        and producer["parent_trace_id"] == verifier["parent_trace_id"]
    )
    producer_cards = producer["cards"]
    if (
        collection.producer_decision_id == collection.verifier_decision_id
        or producer["child_id"] == verifier["child_id"]
        or not same_parent
        or len(producer_cards) != 1
        or producer_cards[0]["specialist_slug"] != ACCEPTED_OUTCOME_CONTRACTOR_SLUG
    ):
        report["unmet_prerequisites"].append(
            "accepted-outcome pair identity or exact contractor attribution was invalid"
        )
        return report

    report["producer"] = producer
    report["verifier"] = verifier
    report["accepted_outcome"] = outcome
    report["child_judge_provider_answered"] = {
        "producer": producer["provider_answered"],
        "verifier": verifier["provider_answered"],
    }
    report["promotion_observed"] = outcome["promoted"] is True
    if (
        collection.reason != "accepted"
        or outcome["reason"] != "accepted"
        or outcome["recorded"] is not True
    ):
        report["unmet_prerequisites"].append(
            f"accepted-outcome Store result was not a fresh acceptance ({collection.reason})"
        )
        return report
    if outcome["artifact_digest"] != producer["artifact_digest"]:
        report["unmet_prerequisites"].append(
            "accepted-outcome Store result did not bind the producer artifact"
        )
        return report
    report["canary_passed"] = True
    report["attestation_persisted"] = False
    return report


__all__ = ["run_accepted_outcome_canary"]
