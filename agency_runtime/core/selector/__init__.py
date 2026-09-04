"""Agency Runtime — Core Selector.

The 8-layer routing pipeline for specialist selection.

Public API:
    route(session_id, user_message, catalog) -> dict
    detect_work_units(message) -> dict
    build_routing_context(routing) -> str
    route_and_build_context(session_id, user_message, catalog) -> str
"""

from agency_runtime.core.selector.cache import (
    cache_get,
    cache_key,
    cache_put,
    clear_cache,
    routing_fingerprint,
)
from agency_runtime.core.selector.candidate_narrow import pre_narrow, score_agent, tokenize

from agency_runtime.core.selector.judge import query_judge
from agency_runtime.core.selector.pipeline import (
    build_routing_context,
    detect_work_units,
    is_trivial,
    refine_query,
    route,
    route_and_build_context,
)
from agency_runtime.core.selector.policy import (
    detect_actions,
    detect_fallback_companions,
    load_policy,
    validate_policy,
)
from agency_runtime.core.selector.stickiness import session_check, session_put
from agency_runtime.core.turn_intent import (
    TurnClassification,
    TurnState,
    classify_turn_intent,
    is_pure_acknowledgement,
)

__all__ = [
    "TurnClassification",
    "TurnState",
    "build_routing_context",
    "cache_get",
    "cache_key",
    "cache_put",
    "classify_turn_intent",
    "clear_cache",
    "detect_actions",
    "detect_fallback_companions",
    "detect_work_units",

    "is_pure_acknowledgement",
    "is_trivial",
    "load_policy",
    "pre_narrow",
    "query_judge",
    "refine_query",
    "route",
    "route_and_build_context",
    "routing_fingerprint",
    "score_agent",
    "session_check",
    "session_put",
    "tokenize",
    "validate_policy",
]
