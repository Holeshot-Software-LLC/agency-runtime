"""Reconcile LiteLLM routing telemetry into one truthful model receipt.

LiteLLM accepts aliases and router model groups at the request boundary, so a
requested ``model`` is never evidence of the deployment that actually ran.
This module keeps the trust order explicit and dependency-free while accepting
both mapping- and attribute-style StandardLoggingPayload objects.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.receipts.ingress import canonicalize_provider

from .evidence import bounded, first, hidden_params, mapping, provider_model, response_value

_MODEL_LIMIT = 256
_PROVIDER_LIMIT = 128
_GROUP_LIMIT = 256


def _field(container: Any, key: str) -> Any:
    """Read one third-party field without assuming a concrete payload class."""

    if isinstance(container, Mapping):
        return container.get(key)
    if container is None:
        return None
    try:
        return getattr(container, key, None)
    except Exception:
        return None


def _nested(container: Any, key: str) -> Any:
    value = _field(container, key)
    return value if isinstance(value, Mapping) or value is not None else {}


def _candidate_model(value: Any) -> tuple[str, str]:
    """Return a bounded provider/model pair from explicit deployment telemetry."""

    provider, model = provider_model(value)
    return bounded(provider, _PROVIDER_LIMIT), bounded(model, _MODEL_LIMIT)


def _alias_identities(value: Any) -> set[str]:
    """Return conservative identities for one possibly decorated route alias.

    LiteLLM integrations have emitted the same router name as an unqualified
    model, a provider-qualified model, and a labelled/decorated value.  These
    lower-trust spellings must compare equal without treating them as proof of
    a deployment.  The expansion intentionally errs toward unavailable model
    evidence when a candidate remains ambiguous with the request route.
    """

    raw = bounded(value, 1024).casefold()
    if not raw:
        return set()
    identities = {raw, raw.rsplit("/", 1)[-1]}
    expanded: set[str] = set()
    pending = list(identities)
    labels = ("alias=", "deployment=", "model=", "route=", "router=")
    while pending:
        candidate = pending.pop().strip().strip("[](){}\"'")
        if not candidate or candidate in expanded:
            continue
        expanded.add(candidate)
        pending.extend(candidate[len(label) :] for label in labels if candidate.startswith(label))
        pending.extend(
            candidate.split(separator, 1)[0]
            for separator in ("?", "#", "@", " (", " [")
            if separator in candidate
        )
        if ":" in candidate:
            prefix, suffix = candidate.split(":", 1)
            pending.extend((prefix, suffix))
    return expanded


def _is_route_alias(value: Any, aliases: set[str]) -> bool:
    return bool(aliases.intersection(_alias_identities(value)))


@dataclass(frozen=True, slots=True)
class ReconciledLiteLLMModel:
    """Bounded model truth and the separate router group that selected it."""

    model_group: str
    resolved_provider: str
    resolved_model: str


def reconcile_litellm_model(
    payload: Mapping[str, Any],
    response_obj: Any,
    *,
    receipt: Mapping[str, Any] | None = None,
    status: str,
) -> ReconciledLiteLLMModel:
    """Reconcile a successful LiteLLM call without promoting request aliases.

    Model truth is selected in this order: the provider-reported response
    model, LiteLLM's standard hidden routed model, its legacy response-hidden
    equivalent, then a small allowlist of deployment metadata. An opaque
    ``model_id`` and the requested ``model`` are deliberately excluded.
    """

    standard = _field(payload, "standard_logging_object")
    standard_hidden = _nested(standard, "hidden_params")
    standard_metadata = _nested(standard, "metadata")
    response_hidden = hidden_params(response_obj)
    params = mapping(payload.get("litellm_params"))
    model_info = mapping(params.get("model_info"))
    normalized_receipt = mapping(receipt)

    model_group = bounded(
        first(
            _field(standard, "model_group"),
            _field(standard_metadata, "model_group"),
            normalized_receipt.get("model_group"),
            response_hidden.get("model_group"),
        ),
        _GROUP_LIMIT,
    )
    if status != "success":
        return ReconciledLiteLLMModel(model_group, "", "unavailable")

    # The response model is normally the strongest execution evidence. Some
    # LiteLLM providers instead echo the requested router alias there, so an
    # exact alias echo yields to a distinct routed/deployment candidate.
    response_candidate_value = response_value(response_obj, "model")
    routed_candidate_values = (
        _field(standard_hidden, "litellm_model_name"),
        response_hidden.get("litellm_model_name"),
        _field(standard_metadata, "deployment"),
        _field(standard_metadata, "deployment_model_name"),
        _field(standard_hidden, "deployment"),
        _field(standard_hidden, "deployment_model_name"),
        model_info.get("base_model"),
        params.get("deployment"),
        params.get("deployment_model_name"),
    )
    response_candidate = _candidate_model(response_candidate_value)
    routed_candidates = [(value, _candidate_model(value)) for value in routed_candidate_values]
    # Providers sometimes qualify an echoed alias (for example,
    # ``openai/production-router``) even when the request and model group use
    # the unqualified ``production-router`` form. Compare the normalized model
    # component as well as the raw value so that provider decoration cannot
    # promote a router alias into actual-model evidence.
    route_alias_identities = _alias_identities(payload.get("model"))
    route_alias_identities.update(_alias_identities(model_group))
    echoed_route_identity = bool(response_candidate[1]) and _is_route_alias(
        response_candidate_value,
        route_alias_identities,
    )
    distinct_routed_candidate = next(
        (
            candidate
            for value, candidate in routed_candidates
            if candidate[1] and not _is_route_alias(value, route_alias_identities)
        ),
        None,
    )
    if response_candidate[1] and echoed_route_identity:
        resolved_provider, resolved_model = distinct_routed_candidate or ("", "")
    elif response_candidate[1]:
        resolved_provider, resolved_model = response_candidate
    else:
        resolved_provider, resolved_model = distinct_routed_candidate or ("", "")

    # An unqualified authoritative model may use explicit transport-provider
    # metadata, but never a provider parsed from a lower-priority, disagreeing
    # model candidate. Requested aliases and model IDs never participate.
    resolved_provider = canonicalize_provider(
        first(
            resolved_provider,
            _field(standard_hidden, "custom_llm_provider"),
            response_hidden.get("custom_llm_provider"),
            params.get("custom_llm_provider"),
            payload.get("custom_llm_provider"),
            normalized_receipt.get("resolved_provider"),
        )
    )
    return ReconciledLiteLLMModel(
        model_group=model_group,
        resolved_provider=resolved_provider,
        resolved_model=resolved_model or "unavailable",
    )


__all__ = ["ReconciledLiteLLMModel", "reconcile_litellm_model"]
