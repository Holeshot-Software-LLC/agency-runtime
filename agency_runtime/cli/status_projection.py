"""Bounded inference-health projections for CLI status.

The dashboard and CLI deliberately share the authoritative core projection.
This module only validates an authenticated dashboard response before the CLI
echoes it, so unknown fields, prompt bodies, and provider secrets cannot cross
the broker boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.dashboard_operational import inference_operational_snapshot
from agency_runtime.core.display import safe_display_token

_PROVIDER_LIMIT = 4
_FAILURE_LIMIT = 25
_STATES = frozenset({"degraded", "not_configured", "operational", "unknown"})
_SCHEMA = "agency.dashboard.inference_operations.v1"


def _text(value: object, *, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError("dashboard inference response contains a non-string token")
    return safe_display_token(value, limit=limit)


def _receipt(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("dashboard inference model receipt must be a JSON object")
    return {
        "requested_model": _text(value.get("requested_model"), limit=256),
        "router": _text(value.get("router"), limit=256),
        "actual_provider": _text(value.get("actual_provider"), limit=128),
        "actual_model": _text(value.get("actual_model"), limit=256),
        "status": _text(value.get("status"), limit=32),
        "host": _text(value.get("host"), limit=64),
        "source": _text(value.get("source"), limit=64),
        "recorded_at": _text(value.get("recorded_at"), limit=128),
    }


def _provider(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("dashboard inference provider entry must be a JSON object")
    order = raw.get("order")
    ready = raw.get("configuration_ready")
    if isinstance(order, bool) or not isinstance(order, int) or not 1 <= order <= _PROVIDER_LIMIT:
        raise ValueError("dashboard inference provider order is invalid")
    if not isinstance(ready, bool):
        raise ValueError("dashboard inference provider readiness is invalid")
    return {
        "order": order,
        "name": _text(raw.get("name"), limit=128),
        "type": _text(raw.get("type"), limit=32),
        "transport": _text(raw.get("transport"), limit=32),
        "requested_model": _text(raw.get("requested_model"), limit=256),
        "router": _text(raw.get("router"), limit=256),
        "configuration_ready": ready,
        "auth_method": _text(raw.get("auth_method"), limit=256),
        "observed_receipt": _receipt(raw.get("observed_receipt")),
    }


def _failure(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("dashboard inference failure entry must be a JSON object")
    kind = _text(raw.get("kind"), limit=32)
    if kind == "model_receipt":
        receipt = _receipt(raw)
        if receipt is None:  # pragma: no cover - mapping input cannot project to None
            raise ValueError("dashboard inference model failure is invalid")
        return {"kind": kind, **receipt}
    if kind == "routing":
        return {
            "kind": kind,
            "status": _text(raw.get("status"), limit=32),
            "provider": _text(raw.get("provider"), limit=128),
            "created_at": _text(raw.get("created_at"), limit=128),
            "trace_id": _text(raw.get("trace_id"), limit=256),
        }
    raise ValueError("dashboard inference failure kind is invalid")


def project_brokered_inference(value: object) -> dict[str, Any]:
    """Validate and allowlist the shared operational inference projection."""

    if not isinstance(value, Mapping):
        raise ValueError("dashboard inference response must be a JSON object")
    if value.get("schema_version") != _SCHEMA:
        raise ValueError("dashboard inference response schema is invalid")
    raw_chain = value.get("provider_chain")
    raw_failures = value.get("recent_failures")
    if (
        not isinstance(raw_chain, list)
        or len(raw_chain) > _PROVIDER_LIMIT
        or not isinstance(raw_failures, list)
        or len(raw_failures) > _FAILURE_LIMIT
    ):
        raise ValueError("dashboard inference response exceeds its bounded collections")
    chain = [_provider(raw) for raw in raw_chain]
    failures = [_failure(raw) for raw in raw_failures]

    configured = value.get("configured")
    required = value.get("required_for_eligible_turns")
    truncated = value.get("failures_truncated")
    state = value.get("state")
    failure_count = value.get("failure_count")
    if (
        not isinstance(configured, bool)
        or not isinstance(required, bool)
        or required is not configured
        or not isinstance(truncated, bool)
        or not isinstance(state, str)
        or state not in _STATES
        or isinstance(failure_count, bool)
        or not isinstance(failure_count, int)
        or failure_count < len(failures)
        or truncated is not (failure_count > len(failures))
    ):
        raise ValueError("dashboard inference response state is internally inconsistent")
    return {
        "schema_version": _SCHEMA,
        "configured": configured,
        "required_for_eligible_turns": required,
        "state": state,
        "evidence": _text(value.get("evidence"), limit=256),
        "provider_chain": chain,
        "latest_model_resolution": _receipt(value.get("latest_model_resolution")),
        "recent_failures": failures,
        "failure_count": failure_count,
        "failures_truncated": truncated,
    }


def direct_inference_snapshot(
    runtime_store: Any,
    config: AgencyConfig,
) -> dict[str, Any]:
    """Build the exact bounded inference projection consumed by the dashboard."""

    activity = runtime_store.recent_dashboard_activity(limit=50)
    return inference_operational_snapshot(config, activity)


__all__ = ["direct_inference_snapshot", "project_brokered_inference"]
