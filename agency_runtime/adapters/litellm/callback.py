"""LiteLLM adapter — callback for LiteLLM proxy.

When LiteLLM is present, this adapter provides the highest-fidelity
model receipt data via response headers and SpendLogs.

All model names, URLs, and skip patterns come from the centralized config.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.litellm")


def litellm_health_check(base_url: str | None = None, config: AgencyConfig | None = None) -> bool:
    """Check if LiteLLM gateway is reachable."""
    cfg = config or load_config()
    url = base_url or cfg.adapters.litellm.base_url
    try:
        req = urllib.request.Request(f"{url}/health/liveness")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


class LiteLLMAdapter(BaseAdapter):
    """LiteLLM proxy adapter.

    Responsibilities:
    - Run pre_call routing when traffic passes through LiteLLM.
    - Extract model receipt from response headers.
    - Record fallback/route audit into SQLite.
    """

    host_name = "litellm"

    def __init__(self, store: Store | None = None, base_url: str | None = None,
                 config: AgencyConfig | None = None):
        super().__init__(store)
        self._config = config or load_config()
        self.base_url = base_url or self._config.adapters.litellm.base_url

    def is_available(self) -> bool:
        enabled = self._config.adapters.litellm.enabled
        if enabled == "false":
            return False
        if enabled == "true":
            return True
        return litellm_health_check(self.base_url, self._config)

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return self.store.get_skills_for_session(session_id)

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        conn = self.store._connect()
        try:
            cur = conn.execute(
                "SELECT agent_slug FROM specialists_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["agent_slug"] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_delegate_backend(self) -> str | None:
        return None  # LiteLLM delegates to host adapters

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        """LiteLLM does not expose telemetry directly; use receipts."""
        return {}

    def extract_receipt_from_headers(
        self, headers: dict[str, str], requested_model: str, trace_id: str = "",
    ) -> dict[str, Any]:
        """Extract model receipt from LiteLLM response headers."""
        from agency_runtime.core.receipts.normalize import normalize_litellm_receipt
        receipt = normalize_litellm_receipt(headers, requested_model)
        if trace_id:
            receipt["trace_id"] = trace_id
        receipt["host"] = self.host_name
        return receipt

    def pre_call_handler(
        self,
        session_id: str,
        user_message: str,
        model: str,
        messages: list[dict] | None = None,
    ) -> dict[str, Any] | None:
        """Pre-call handler for LiteLLM proxy.

        Runs the routing pipeline and returns context injection.
        Returns None for infrastructure calls or trivial messages.
        """
        from agency_runtime.core.selector.pipeline import is_trivial, route_and_build_context

        # Skip routing for models in the config's skip_models list
        skip_models = self._config.adapters.litellm.skip_models
        if any(pattern in model.lower() for pattern in skip_models):
            return None

        if is_trivial(user_message, self._config):
            return None

        catalog = self.store.get_active_roster_as_catalog()
        context = route_and_build_context(session_id, user_message, catalog, config=self._config)
        return {"context": context} if context else None
