"""Deterministic authority ordering for correlated model receipts."""

from __future__ import annotations

# This expression is an internal SQL constant, never caller-controlled. A
# concrete successful model is stronger than a later unavailable observation;
# LiteLLM telemetry is stronger than generic host telemetry when quality is
# equal because only LiteLLM preserves the authoritative router/model-group
# identity; ingestion chronology remains the tiebreak within equal authority.
MODEL_RECEIPT_AUTHORITY_ORDER_SQL = """
CASE
    WHEN LOWER(COALESCE(status, '')) IN ('success', 'completed', 'ok')
         AND TRIM(COALESCE(resolved_model, '')) <> ''
         AND LOWER(TRIM(COALESCE(resolved_model, ''))) <> 'unavailable' THEN 4
    WHEN LOWER(COALESCE(status, '')) NOT IN
         ('failed', 'failure', 'error', 'cancelled', 'canceled', 'timed_out', 'timeout')
         AND TRIM(COALESCE(resolved_model, '')) <> ''
         AND LOWER(TRIM(COALESCE(resolved_model, ''))) <> 'unavailable' THEN 3
    WHEN LOWER(COALESCE(status, '')) IN ('success', 'completed', 'ok') THEN 2
    WHEN LOWER(COALESCE(status, '')) NOT IN
         ('failed', 'failure', 'error', 'cancelled', 'canceled', 'timed_out', 'timeout') THEN 1
    ELSE 0
END DESC,
CASE LOWER(TRIM(COALESCE(source, '')))
    WHEN 'litellm' THEN 3
    WHEN 'host' THEN 2
    WHEN 'wrapper' THEN 1
    ELSE 0
END DESC,
recorded_at DESC,
rowid DESC
""".strip()


__all__ = ["MODEL_RECEIPT_AUTHORITY_ORDER_SQL"]
