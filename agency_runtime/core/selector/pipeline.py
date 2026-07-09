"""Full 8-layer routing pipeline — the core selector.

Uses centralized config for all tunable values.

Layer 0: Companion policy (deterministic action→agent mapping, <1ms)
Layer 1: Domain context expansion
Layer 2: LRU cache (content-hash + TTL)
Layer 3: Session stickiness (token overlap reuse)
Layer 4: Confidence bypass (skip LLM when token score ≥ threshold)
Layer 5: Token pre-narrow + LLM judge
Layer 6: Token-only fallback (if LLM unavailable)
Layer 7: Union companion policy results with semantic results
"""

from __future__ import annotations

import logging
import re
from typing import Any

from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.selector.cache import cache_get, cache_key, cache_put
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.candidate_narrow import tokenize
from agency_runtime.core.selector.policy import detect_actions
from agency_runtime.core.selector.stickiness import session_check, session_put
from agency_runtime.core.selector.judge import query_judge

logger = logging.getLogger("agency_runtime.selector.pipeline")


def _get_config(config: AgencyConfig | None = None) -> AgencyConfig:
    return config or load_config()


def refine_query(user_message: str, config: AgencyConfig | None = None) -> str:
    """Lightweight query refinement without an LLM call."""
    cfg = _get_config(config)
    msg = user_message.strip()
    msg = re.sub(r"^(?:Hermes|Mentor|Nexus|OpenClaw)\s*[:,-]?\s*", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"https?://\S+", "", msg)
    msg = re.sub(r"/(?:home|usr|opt|var|tmp)/\S+", "", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    max_len = cfg.selector.max_user_msg_len
    if len(msg) > max_len:
        msg = msg[:max_len]
    return msg


def is_trivial(message: str, config: AgencyConfig | None = None) -> bool:
    """Check if a message is too trivial to warrant agency routing."""
    cfg = _get_config(config)
    msg = message.strip()
    if len(msg) < cfg.selector.trivial_msg_threshold:
        return True
    return bool(_TRIVIAL_PATTERNS.match(msg))


_TRIVIAL_PATTERNS = re.compile(
    r"^(?:yes|no|ok|okay|sure|thanks|done|got ?it|cool|nice|great|"
    r"perfect|exactly|right|correct|yep|nope|true|false|"
    r"continue|proceed|go|stop|wait|hold|skip|next|retry|"
    r"hello|hi|hey|sup|yo|test|ping|status|heartbeat"
    r"|/\w+|ack|k|thx|ty|np|lol|haha|👍|❤️|🙌|✅|💀|😂)\s*[!.?]*$",
    re.IGNORECASE,
)


def route(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    *,
    config: AgencyConfig | None = None,
) -> dict[str, Any]:
    """Run the full 8-layer routing pipeline.

    Args:
        session_id: Session identifier for stickiness.
        user_message: The user's raw message text.
        catalog: Agent catalog to route against. If None, caller must provide.
        config: Optional config override.

    Returns:
        Routing dict with keys: selected_ids, confidence, latency_ms, status,
        companion_actions, companion_ids, work_units, and possibly cache_hit,
        session_reused.
    """
    cfg = _get_config(config)
    if catalog is None:
        catalog = []

    # Layer 0: Companion policy + work unit decomposition
    matched_actions, companion_ids = detect_actions(user_message)
    work_units = detect_work_units(user_message)

    refined = expand_query(refine_query(user_message, cfg))

    # Layer 2: Cache
    key = cache_key(refined)
    cached = cache_get(key)
    if cached is not None:
        cached_ids = cached.get("selected_ids", [])
        merged = list(cached_ids)
        for cid in companion_ids:
            if cid not in merged:
                merged.append(cid)
        if len(merged) > len(cached_ids):
            cached["selected_ids"] = merged
            cached["companion_actions"] = matched_actions
        return cached

    # Layer 3: Session stickiness
    session_result = session_check(session_id, refined)
    if session_result is not None:
        session_ids = session_result.get("selected_ids", [])
        merged = list(session_ids)
        for cid in companion_ids:
            if cid not in merged:
                merged.append(cid)
        if len(merged) > len(session_ids):
            session_result["selected_ids"] = merged
            session_result["companion_actions"] = matched_actions
        return session_result

    # Layer 4-6: Pre-narrow + LLM judge + fallback
    routing = query_judge(refined, catalog, config=cfg)

    # Layer 7: Union companion policy with semantic results
    semantic_ids = routing.get("selected_ids", [])
    merged_ids = list(semantic_ids)
    for cid in companion_ids:
        if cid not in merged_ids:
            merged_ids.append(cid)
    routing["selected_ids"] = merged_ids
    routing["companion_actions"] = matched_actions
    routing["companion_ids"] = companion_ids
    routing["work_units"] = work_units

    if routing.get("selected_ids"):
        cache_put(key, routing)
        session_put(session_id, refined, routing)

    return routing


def build_routing_context(routing: dict[str, Any], config: AgencyConfig | None = None) -> str:
    """Build the [AGENCY PREFLIGHT] context string from a routing result."""
    cfg = _get_config(config)
    selected = routing.get("selected_ids", [])
    confidence = routing.get("confidence", 0.0)
    cache_hit = routing.get("cache_hit", False)
    session_reused = routing.get("session_reused", False)
    status = routing.get("status", "unknown")

    source = "llm"
    if cache_hit:
        source = "cache"
    elif session_reused:
        source = "session"

    parts: list[str] = []

    if not selected or confidence < cfg.selector.min_confidence:
        parts.append(
            f"[AGENCY PREFLIGHT] No high-confidence specialist match found "
            f"(status={status}). You must still query "
            "agency_agents_search before any non-trivial work and include "
            "the Agency header in your response."
        )
        parts.append(HEADER_INSTRUCTION)
        return "\n".join(parts)

    agents_list = ", ".join(selected)
    parts.append(
        f"[AGENCY PREFLIGHT] Specialist routing suggestion "
        f"(confidence={confidence:.1f}, source={source}): {agents_list}"
    )

    work_units = routing.get("work_units", {})
    if work_units.get("delegate", False) and work_units.get("count", 1) >= 2:
        unit_count = work_units["count"]
        unit_source = work_units.get("source", "unknown")
        unit_confidence = work_units.get("confidence", "low")
        units_list = work_units.get("units", [])

        nudge = (
            f"\n\n[DELEGATION OPPORTUNITY] {unit_count} independent work units "
            f"detected (confidence={unit_confidence}, source={unit_source}). "
            "PRIORITY: delegate parallel work via delegate_task or delegate_async. "
            "Keep the main session available for the user."
        )
        if units_list:
            nudge += "\n  Detected work units:"
            for i, unit in enumerate(units_list, 1):
                nudge += f"\n    {i}. {unit}"
        parts.append(nudge)

    parts.append(HEADER_INSTRUCTION)
    return "\n".join(parts)


def route_and_build_context(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    config: AgencyConfig | None = None,
) -> str | None:
    """Run the full pipeline and return the context string. None if trivial."""
    cfg = _get_config(config)
    if is_trivial(user_message, cfg):
        return None
    routing = route(session_id, user_message, catalog, config=cfg)
    return build_routing_context(routing, cfg)


HEADER_INSTRUCTION = (
    "\n  You MUST call agency_agents_search and/or agency_agents_load "
    "for the relevant specialist(s) before starting non-trivial work, "
    "and include the Agency header in your response:\n"
    "  Agency/Agencies loaded: <agent-id>\n"
    "  Agency/Agencies delegated: <agent-id>\n"
    "  Skills loaded: <skill-id[, skill-id...] or none>\n"
    "  Actual Model selected: <requested alias> -> <resolved provider/model>\n"
    "  Why: <one line>\n"
    "  How it shaped outcome: <one line>"
)
